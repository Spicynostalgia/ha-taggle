#!/usr/bin/env python3
"""Render redacted figures from read-only Taggle recordings and the real receiver.

Example (NumPy, SciPy, matplotlib and the decoder's CLI dependencies installed):
  OPENBLAS_NUM_THREADS=2 python make_figures.py --captures /path/to/captures \
    --analysis /path/to/analysis --decoder /path/to/ha-taggle

No IQ, decoded payload, unredacted log or cumulative counter is written. The
CLI scan is captured in memory and redacted before rendering or saving text.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
from scipy import fft, signal

RATE = 2_400_000
CENTRE_MHZ = 922.2
INK, BLUE, GREEN, PURPLE = '#172c3c', '#075e91', '#166846', '#7451a5'


def mask_id(value):
    text = str(int(value))
    return text[:2] + 'x' * (len(text)-2)


def safe_hex(text, encrypted=False):
    """Keep framing/format/flags only; redact whole ID and every usage field.

    The 20-bit ID crosses byte boundaries, so nibble masking is mandatory.
    Redact CRC bytes too: truncated header checks can constrain a masked ID.
    Ciphertext is represented by opaque blocks rather than published bytes.
    """
    keep = {0, 1, 9}
    if not encrypted:
        keep |= {17, 22, 27}
    return ''.join(c.upper() if i in keep else 'X' for i, c in enumerate(text))


def save(fig, name, out, provenance):
    fig.savefig(out / (name + '.png'), dpi=160, facecolor='white',
                metadata={'Software': 'matplotlib', 'Description': provenance})
    labels = [t.get_text() for t in fig.findobj(matplotlib.text.Text) if t.get_text()]
    (out / (name + '.labels.json')).write_text(json.dumps(labels, ensure_ascii=False, indent=2)+'\n')
    plt.close(fig)


def box(ax, x, y, w, h, title, body, color=BLUE):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012',
                 facecolor='#f4f8fa',edgecolor=color,linewidth=1.2))
    ax.text(x+w/2,y+h*.69,title,ha='center',va='center',weight='bold',color=color)
    ax.text(x+w/2,y+h*.28,body,ha='center',va='center',fontsize=10,color=INK)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', required=True, type=Path)
    parser.add_argument('--analysis', required=True, type=Path)
    parser.add_argument('--decoder', required=True, type=Path)
    parser.add_argument('--out', type=Path, default=Path(__file__).parent/'img')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.decoder/'addon'))
    from taggle_rx.receiver import iq, Detector, PERIOD, BLOCK
    from taggle_rx.dsss import recover_dsss, predicted_template
    from taggle_rx.protocol import lfsr, decode_frame
    from taggle_rx.coding import convolution_decode_viterbi, crc_bits, convolution_encode

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,
        'text.color':INK,'axes.labelcolor':INK,'axes.edgecolor':'#748592',
        'xtick.color':INK,'ytick.color':INK,'axes.spines.top':False,
        'axes.spines.right':False,'axes.titleweight':'bold', 'axes.titlesize':13,
        'figure.constrained_layout.use':True})
    frames = [json.loads(line) for line in (args.analysis/'live/full-frames.jsonl').open()]
    clear = next(f for f in frames if f['format_bytes']==18)
    encrypted = next(f for f in frames if f['format_bytes']==24)
    source = args.captures/'iq-922200k-g40-3900s.cu8'
    # Read only 1.2 seconds (~5.8 MB), including quiet padding on either side.
    start = int(clear['sample_offset']/RATE*RATE)-int(.4*RATE)
    with source.open('rb') as stream:
        stream.seek(2*start)
        raw = stream.read(2*int(1.2*RATE))
    z = iq(raw)
    detector = Detector()
    hits = [h for k in range(0,len(raw)-2*BLOCK+1,2*BLOCK)
            if (h := detector.detect(raw[k:k+2*BLOCK]))]
    if not hits:
        raise RuntimeError('real receiver did not acquire the selected slice')
    hit = max(hits,key=lambda h:h['pn_peak_ratio'])
    result = recover_dsss(z,hit['carrier_offset_hz'],PERIOD,.43*RATE,.68*RATE,RATE)
    frame = decode_frame(result['bits'])
    if frame['meter_id'] != clear['id_decimal'] or frame['format_bytes'] != 18:
        raise RuntimeError('recovered slice disagrees with research frame')
    plain, errors = convolution_decode_viterbi(result['bits'][104:])
    payload = np.packbits(plain).tobytes()
    assert payload.hex() == clear['decoded_frame_hex'].lower()
    assert np.array_equal(convolution_encode(plain), result['bits'][104:])
    header_ok = crc_bits(plain[8:36],8,7)==0
    frame_ok = crc_bits(plain[8:-16],8,7)==payload[-2]
    assert header_ok and frame_ok
    # Verify the real encrypted record's outer framing, without interpreting body.
    encrypted_air = np.unpackbits(np.frombuffer(bytes.fromhex(encrypted['on_air_bits_hex']),np.uint8))[:encrypted['symbols']]
    encrypted_decoded = decode_frame(encrypted_air)
    assert encrypted_decoded['encrypted'] and 'counts' not in encrypted_decoded
    prov = 'Real cu8 slice; 2.4 MS/s, 922.2 MHz centre. IDs, counters and payload bits withheld.'

    # 1: full-band occupancy from measured survey bins, plus actual burst spectrum.
    bins = np.genfromtxt(args.analysis/'bins.csv',delimiter=',',names=True)
    fig, ax = plt.subplots(2,1,figsize=(10,6.4))
    ax[0].plot(bins['frequency_hz']/1e6,100*bins['occupancy'],color=BLUE,lw=.8)
    ax[0].set(xlim=(915,928),ylim=(0,20),xlabel='Frequency (MHz)',ylabel='Occupancy (%)',
              title='915–928 MHz survey: excursions ≥6 dB above each bin’s median')
    ax[0].axvline(921.995,color=PURPLE,ls='--',lw=1)
    ax[0].annotate('Later confirmed Taggle channel\n(not an identity from the sweep)',
                   xy=(921.995,17),xytext=(923,13),fontsize=10,
                   arrowprops={'arrowstyle':'->','color':PURPLE})
    a,b=int(result['first_sample']),int(result['last_sample'])
    f,p=signal.welch(z[a:b],fs=RATE,nperseg=2048,return_onesided=False)
    q=np.argsort(f)
    ax[1].plot(CENTRE_MHZ+f[q]/1e6,10*np.log10(p[q]+1e-20),color=BLUE,lw=.9)
    ax[1].axvline(CENTRE_MHZ+hit['carrier_offset_hz']/1e6,color=PURPLE,ls='--')
    ax[1].set(xlabel='Frequency (MHz)',ylabel='PSD (relative dB/Hz)',
              title='Confirmed burst, observed through the RTL-SDR’s 2.4 MHz passband')
    save(fig,'01-band-occupancy',args.out,prov+' Survey occupancy from bins.csv; 409 sweep times, not simultaneous RF.')

    # 2: time-domain envelope and spectrogram, with relative timing only.
    fig,ax=plt.subplots(2,1,figsize=(10,6.5))
    n=1200
    power=np.mean(abs(z[:len(z)//n*n].reshape(-1,n))**2,axis=1)
    ax[0].plot(np.arange(len(power))*n/RATE,10*np.log10(power/(2*127.5**2)),color=BLUE,lw=1)
    ax[0].axvspan(a/RATE,b/RATE,color='#dceef5',zorder=-1)
    ax[0].set(xlabel='Time within private slice (s)',ylabel='Total power (dBFS)',title='One real burst: RF power, averaged over 0.5 ms')
    f,t,s=signal.spectrogram(z,fs=RATE,nperseg=1024,noverlap=0,return_onesided=False)
    order=np.argsort(f)
    db=10*np.log10(s[order]+1e-20)
    im=ax[1].pcolormesh(t,CENTRE_MHZ+f[order]/1e6,db,
                       cmap='Blues',vmin=float(np.percentile(db,15)),
                       vmax=float(np.percentile(db,99)),rasterized=True,shading='auto')
    ax[1].set(xlabel='Time within private slice (s)',ylabel='Frequency (MHz)',title='Spectrogram of the same cu8 samples')
    fig.colorbar(im,ax=ax[1],label='PSD (relative dB/Hz)')
    save(fig,'02-single-burst',args.out,prov)

    # 3: recovered waveform correlated against the clean generated PN sequence.
    v=result['template']
    code=(lfsr()>0).astype(np.uint8)
    predicted=predicted_template(code,len(v),result['period_samples'],RATE,hit['carrier_offset_hz'],0)
    corr=abs(fft.ifft(fft.fft(v)*fft.fft(predicted).conj()))
    lag=np.arange(len(v))*4095/len(v)
    peak=int(corr.argmax())
    fig,ax=plt.subplots(figsize=(10,4))
    ax.plot(lag,corr/corr.max(),color=BLUE,lw=1)
    ax.annotate('Measured peak against the\n4095-chip generated sequence',
                xy=(lag[peak],1),xytext=(900,.72),fontsize=11,
                arrowprops={'arrowstyle':'->','color':BLUE})
    ax.set(xlabel='Cyclic PN offset (chips; arbitrary origin)',ylabel='Correlation / measured peak',
           ylim=(0,1.12),title='PN match after carrier removal, using a partial-band template')
    save(fig,'03-pn-correlation',args.out,prov+' Peak normalised; not a full-band chip autocorrelation.')

    # 4: retain actual complex projections, not a generated ideal constellation.
    before=result['correlations'][result['active_start']:result['active_end']]
    after=result['corrected']
    scale=np.median(abs(after))
    fig,axes=plt.subplots(1,2,figsize=(10,4.7))
    for ax,points,title in zip(axes,[before,after],['Despread; coarse carrier removed','Residual carrier / phase corrected']):
        points=points/scale
        ax.scatter(points.real,points.imag,s=9,alpha=.55,color=BLUE)
        ax.axhline(0,color='#ccd7dd',lw=.8); ax.axvline(0,color='#ccd7dd',lw=.8)
        ax.set(xlabel='I / median amplitude',ylabel='Q / median amplitude',title=title,
               xlim=(-1.7,1.7),ylim=(-1.7,1.7),aspect='equal')
    save(fig,'04-bpsk-constellation',args.out,prov+' Before = pre-Costas symbol projections; already coarse-carrier corrected.')

    # 5: actual FEC result and checks. No raw coded bits that could reveal IDs.
    fig,ax=plt.subplots(figsize=(10,4.8)); ax.set_axis_off()
    box(ax,.03,.68,.25,.23,'392 air symbols','104 preamble + 288 coded')
    box(ax,.37,.68,.25,.23,'Rate 1/2, K = 7','Viterbi → 144 bits')
    box(ax,.71,.68,.25,.23,'18-byte frame',f'{errors} corrected coded bits')
    for x in (.29,.63): ax.annotate('',xy=(x+.07,.8),xytext=(x,.8),arrowprops={'arrowstyle':'->','color':INK})
    box(ax,.08,.29,.38,.23,'Header CRC-8: PASS','bits [8:36] → residue 0',GREEN)
    box(ax,.54,.29,.38,.23,'Frame CRC-8: PASS','bits [8:N−16] → stored CRC',GREEN)
    ax.text(.5,.13,'Polynomial 0x07 · init 0 · no reflection · xorout 0',ha='center',fontsize=11)
    ax.text(.5,.03,'Sync C0 and zero tail also verified. Payload bits withheld for privacy.',ha='center',fontsize=10)
    save(fig,'05-fec-and-crcs',args.out,prov+' Viterbi explicitly rerun; production exact-inversion path also passes.')

    # 6/7: true nibble positions; actual identifiers/counters never sent to text().
    def layout(record,name,opaque=False):
        text=safe_hex(record['decoded_frame_hex'],opaque)
        fig,ax=plt.subplots(figsize=(10,6.5)); ax.set_axis_off()
        ax.set_title(('24-byte encrypted frame' if opaque else '18-byte clear frame')+' · redacted real record',pad=15)
        display=' '.join(text[i:i+2] for i in range(0,len(text),2))
        lines=[display[i:i+35] for i in range(0,len(display),36)]
        for i,line in enumerate(lines):
            ax.text(.04,.91-i*.07,line,fontfamily='DejaVu Sans Mono',fontsize=13)
        if opaque:
            box(ax,.03,.52,.29,.18,'Header / clear ID',f'C0 · {mask_id(record["id_decimal"])}\nID: bits 8–27',BLUE)
            box(ax,.36,.52,.28,.18,'Header CRC-8','bits 28–35 · PASS',GREEN)
            box(ax,.68,.52,.29,.18,'Frame CRC / tail','last 2 bytes · PASS',GREEN)
            box(ax,.03,.23,.61,.22,'Opaque body: bits 36–175','Ciphertext withheld · no usage decoded',PURPLE)
            box(ax,.68,.23,.29,.22,'RF diagnostics',f'SNR {record["snr_median_db"]:.1f} dB\n{record["format_bytes"]} bytes · FEC {record["fec_errors"]}',BLUE)
            ax.text(.5,.10,'Clear framing is readable. AES keys are held by the utility.',ha='center',fontsize=11)
        else:
            box(ax,.03,.60,.28,.16,'Sync / header','C0 · bits 0–7',BLUE)
            box(ax,.36,.60,.28,.16,'Clear ID: '+mask_id(record['id_decimal']),'XXXXX · bits 8–27',BLUE)
            box(ax,.68,.60,.29,.16,'Header CRC-8','bits 28–35 · PASS',GREEN)
            for x,title,span in ((.03,'Newest counter','18–21'),(.36,'Previous counter','23–26'),(.68,'Oldest counter','28–31')):
                box(ax,x,.36,.28,.16,title,f'XXXX · nibbles {span}',BLUE)
            box(ax,.03,.17,.61,.12,'Flags: meanings unknown','nibbles 17, 22, 27 · excluded from arithmetic',PURPLE)
            box(ax,.68,.17,.29,.12,'Frame CRC / tail','last 2 bytes · PASS',GREEN)
            ax.text(.5,.09,'Illustrative counters only: 120, 110, 104 (newest first)',ha='center',fontsize=10)
            ax.text(.5,.045,'Hourly deltas: (120 − 110) mod 65536 = 10; (110 − 104) mod 65536 = 6',ha='center',fontsize=10)
        ax.text(.5,.01,'X masks IDs, checksums, unknown fields and absolute counters. Nibbles indexed from zero.',ha='center',fontsize=9)
        save(fig,name,args.out,prov+' Actual redacted frame; 120/110/104 is a detached illustrative example, not measured counters.')
    layout(clear,'06-clear-frame')
    layout(encrypted,'07-encrypted-frame',True)

    # 8: actual production CLI, scan mode, no configured IDs or disk/MQTT output.
    env=os.environ.copy(); env['PYTHONPATH']=str(args.decoder/'addon'); env['PYTHONDONTWRITEBYTECODE']='1'
    with tempfile.TemporaryDirectory(prefix='taggle-blog-') as temporary:
        temp=Path(temporary)
        (temp/'slice.cu8').write_bytes(raw)
        (temp/'config.json').write_text('{}')
        run=subprocess.run([sys.executable,'-m','taggle_rx','--config',str(temp/'config.json'),
            '--input',str(temp/'slice.cu8'),'--start-utc','2026-01-01T00:00:00+00:00','--scan','1'],
            env=env,capture_output=True,text=True,check=True)
    logs=[]
    for line in run.stdout.splitlines():
        row=json.loads(line)
        row['meter_id']=mask_id(row['meter_id'])
        # Relative time avoids publishing a household's absolute reception time.
        row.pop('time',None); row.pop('counts',None)
        logs.extend(['{',f'  "meter_id": "{row["meter_id"]}",',
                     f'  "snr_median_db": {row["snr_median_db"]},',
                     f'  "signal_level_dbfs": {row["signal_level_dbfs"]}','}'])
    assert logs, 'production CLI must emit a real frame'
    lines=['$ python -m taggle_rx … --input slice.cu8 --scan 1',
           '# Production CLI replay; IDs masked; timestamp omitted.']+logs
    safe_log='\n'.join(lines)+'\n'
    (args.out/'receiver-log.txt').write_text(safe_log)
    fig,ax=plt.subplots(figsize=(10,3.6)); ax.set_axis_off()
    ax.text(.025,.96,safe_log,va='top',fontfamily='DejaVu Sans Mono',fontsize=12,linespacing=1.55)
    save(fig,'08-receiver-log',args.out,prov+' Actual production CLI stdout; date is a placeholder, omitted from output.')
    report={'source':'iq-922200k-g40-3900s.cu8; bounded 1.2-second read',
        'slice_sha256':hashlib.sha256(raw).hexdigest(),
        'sample_rate_msps':2.4,'centre_mhz':922.2,
        'clear_id':mask_id(clear['id_decimal']),'encrypted_id':mask_id(encrypted['id_decimal']),
        'header_crc_pass':bool(header_ok),'frame_crc_pass':bool(frame_ok),
        'viterbi_corrections':int(errors),'cli_replayed':True,
        'privacy':'No raw bits, full IDs, timestamps, ciphertext or cumulative counters published.',
        'decoder_commit':subprocess.check_output(['git','-C',str(args.decoder),'rev-parse','HEAD'],text=True).strip(),
        'figures':[p.name for p in sorted(args.out.glob('*.png'))]}
    (args.out/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Rendered eight redacted figures; real CLI replay and both CRC checks passed.')


if __name__=='__main__':
    main()
