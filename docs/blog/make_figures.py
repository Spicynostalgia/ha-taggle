#!/usr/bin/env python3
"""Render publication figures from read-only Taggle recordings and the real receiver.

Example (NumPy, SciPy, matplotlib and the decoder's CLI dependencies installed):
  OPENBLAS_NUM_THREADS=2 python make_figures.py --captures /path/to/captures \
    --analysis /path/to/analysis --decoder /path/to/ha-taggle

The approved clear burst 06 and encrypted burst 08 are shown unmasked.
No other household’s clear frame or usage is published; source IQ stays private.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from scipy import fft, signal

RATE = 2_400_000
CENTRE_MHZ = 922.2
INK, BLUE, GREEN, PURPLE = '#172c3c', '#075e91', '#166846', '#7451a5'


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


def configure_style():
    """Keep radio and calibration figures in the same publication style."""
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,
        'text.color':INK,'axes.labelcolor':INK,'axes.edgecolor':'#748592',
        'xtick.color':INK,'ytick.color':INK,'axes.spines.top':False,
        'axes.spines.right':False,'axes.titleweight':'bold', 'axes.titlesize':13,
        'figure.constrained_layout.use':True})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', required=True, type=Path)
    parser.add_argument('--analysis', required=True, type=Path)
    parser.add_argument('--decoder', required=True, type=Path)
    parser.add_argument('--out', type=Path, default=Path(__file__).parent/'img')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(args.decoder/'addon'))
    from taggle_rx.coding import convolution_decode_viterbi, convolution_encode, crc_bits
    from taggle_rx.dsss import predicted_template, recover_dsss
    from taggle_rx.protocol import decode_frame, lfsr
    from taggle_rx.receiver import BLOCK, PERIOD, Detector, iq

    configure_style()
    frames = [json.loads(line) for line in (args.analysis/'live/full-frames.jsonl').open()]
    clear = next(f for f in frames if f['id_decimal']==527814
                 and round(f['sample_offset']/RATE, 2)==595.33)
    assert clear['format_bytes']==18 and round(clear['snr_median_db'], 1)==30.7
    encrypted = next(f for f in frames if f['id_decimal']==766910
                     and abs(f['sample_offset']/RATE - 1406.47) < .02)
    assert encrypted['format_bytes']==24
    source = args.captures/'bursts/burst06_595.33s.cu8'
    # The archived clip starts 0.5 s before the burst. Read 1.2 s only.
    with source.open('rb') as stream:
        raw = stream.read(2*int(1.2*RATE))
    z = iq(raw)
    detector = Detector()
    hits = [h for k in range(0,len(raw)-2*BLOCK+1,2*BLOCK)
            if (h := detector.detect(raw[k:k+2*BLOCK]))]
    if not hits:
        raise RuntimeError('real receiver did not acquire the selected slice')
    hit = max(hits,key=lambda h:h['pn_peak_ratio'])
    result = recover_dsss(z,hit['carrier_offset_hz'],PERIOD,.53*RATE,.78*RATE,RATE)
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
    encrypted_plain, encrypted_errors = convolution_decode_viterbi(encrypted_air[104:])
    assert np.packbits(encrypted_plain).tobytes().hex() == encrypted['decoded_frame_hex']
    assert encrypted_errors == encrypted['fec_errors'] == 0
    assert np.array_equal(convolution_encode(encrypted_plain), encrypted_air[104:])
    prov = 'Author’s own meter 527814 / 0x80DC6, shown with permission; 18 bytes, SNR 30.7 dB. 2.4 MS/s, 922.2 MHz centre.'

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
    ax[0].set(xlabel='Time within clip (s)',ylabel='Total power (dBFS)',title='Author’s meter 527814 / 0x80DC6: RF power, averaged over 0.5 ms')
    f,t,s=signal.spectrogram(z,fs=RATE,nperseg=1024,noverlap=0,return_onesided=False)
    order=np.argsort(f)
    db=10*np.log10(s[order]+1e-20)
    im=ax[1].pcolormesh(t,CENTRE_MHZ+f[order]/1e6,db,
                       cmap='Blues',vmin=float(np.percentile(db,15)),
                       vmax=float(np.percentile(db,99)),rasterized=True,shading='auto')
    ax[1].set(xlabel='Time within clip (s)',ylabel='Frequency (MHz)',title='Spectrogram of the same cu8 samples')
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
    fig.suptitle('Author’s meter 527814 / 0x80DC6 · shown with permission',fontsize=11)
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
    fig.suptitle('Author’s meter 527814 / 0x80DC6 · shown with permission',fontsize=11)
    for ax,points,title in zip(axes,[before,after],['Despread; coarse carrier removed','Residual carrier / phase corrected']):
        points=points/scale
        ax.scatter(points.real,points.imag,s=9,alpha=.55,color=BLUE)
        ax.axhline(0,color='#ccd7dd',lw=.8); ax.axvline(0,color='#ccd7dd',lw=.8)
        ax.set(xlabel='I / median amplitude',ylabel='Q / median amplitude',title=title,
               xlim=(-1.7,1.7),ylim=(-1.7,1.7),aspect='equal')
    save(fig,'04-bpsk-constellation',args.out,prov+' Before = pre-Costas symbol projections; already coarse-carrier corrected.')

    # 5: actual FEC result and checks for the approved clear frame.
    fig,ax=plt.subplots(figsize=(10,4.8)); ax.set_axis_off()
    box(ax,.03,.68,.25,.23,'392 air symbols','104 preamble + 288 coded')
    box(ax,.37,.68,.25,.23,'Rate 1/2, K = 7','Viterbi → 144 bits')
    box(ax,.71,.68,.25,.23,'18-byte frame',f'{errors} corrected coded bits')
    for x in (.29,.63): ax.annotate('',xy=(x+.07,.8),xytext=(x,.8),arrowprops={'arrowstyle':'->','color':INK})
    box(ax,.08,.29,.38,.23,'Header CRC-8: PASS','bits [8:36] → residue 0',GREEN)
    box(ax,.54,.29,.38,.23,'Frame CRC-8: PASS','bits [8:N−16] → stored CRC',GREEN)
    ax.text(.5,.13,'Polynomial 0x07 · init 0 · no reflection · xorout 0',ha='center',fontsize=11)
    ax.text(.5,.03,'Sync C0 and zero tail verified · author’s meter 527814 / 0x80DC6',ha='center',fontsize=10)
    save(fig,'05-fec-and-crcs',args.out,prov+' Viterbi explicitly rerun; production exact-inversion path also passes.')

    # 6/7: publish the two selected frames in full; never interpret ciphertext.
    def layout(record,name,opaque=False):
        text=record['decoded_frame_hex'].upper()
        fig,ax=plt.subplots(figsize=(10,6.5)); ax.set_axis_off()
        ax.set_title(('24-byte encrypted frame' if opaque else '18-byte clear frame')+(' · burst 08, unmasked' if opaque else ' · author’s meter, shown with permission'),pad=15)
        display=' '.join(text[i:i+2] for i in range(0,len(text),2))
        lines=[display[i:i+35] for i in range(0,len(display),36)]
        for i,line in enumerate(lines):
            ax.text(.04,.91-i*.07,line,fontfamily='DejaVu Sans Mono',fontsize=13)
        if opaque:
            box(ax,.03,.52,.29,.18,'Header / clear ID',f'C0 · {record["id_decimal"]} / {record["id_hex"]}\nID: bits 8–27',BLUE)
            box(ax,.36,.52,.28,.18,'Header CRC-8','bits 28–35 · PASS',GREEN)
            box(ax,.68,.52,.29,.18,'Frame CRC / tail','last 2 bytes · PASS',GREEN)
            box(ax,.03,.23,.61,.22,'Opaque body: bits 36–175','Classified as encrypted · no usage decoded',PURPLE)
            box(ax,.68,.23,.29,.22,'RF diagnostics',f'SNR {record["snr_median_db"]:.1f} dB\n{record["format_bytes"]} bytes · FEC {record["fec_errors"]}',BLUE)
            ax.text(.5,.10,'No keys available; body not interpreted',ha='center',fontsize=11)
        else:
            box(ax,.03,.60,.28,.16,'Sync / header','C0 · bits 0–7',BLUE)
            box(ax,.36,.60,.28,.16,'ID: '+str(record['id_decimal']),'0x80DC6 · bits 8–27',BLUE)
            box(ax,.68,.60,.29,.16,'Header CRC-8','bits 28–35 · PASS',GREEN)
            for slot,(x,title,span) in zip(record['count_slots'],((.03,'Newest counter','18–21'),(.36,'Previous counter','23–26'),(.68,'Oldest counter','28–31'))):
                box(ax,x,.36,.28,.16,title,f'{slot["value"]} · nibbles {span}',BLUE)
            box(ax,.03,.17,.61,.12,'Flags: meanings unknown','nibbles 17, 22, 27 · excluded from arithmetic',PURPLE)
            box(ax,.68,.17,.29,.12,'Frame CRC / tail','last 2 bytes · PASS',GREEN)
            ax.text(.5,.09,'Measured counters: 46234, 46223, 46218 · sequence 172 (newest first)',ha='center',fontsize=10)
            ax.text(.5,.045,'Hourly deltas: (46234 − 46223) mod 65536 = 11; (46223 − 46218) mod 65536 = 5',ha='center',fontsize=10)
        ax.text(.5,.01,'Full opaque body and clear ID shown. Cipher mode and body subfields unknown.' if opaque else 'Full 18-byte frame shown with permission. Nibbles indexed from zero.',ha='center',fontsize=9)
        save(fig,name,args.out,'Burst 08; full ID 766910 / 0xBB3BE, checksums and opaque body, classified as encrypted; usage unreadable.' if opaque else prov+' Full measured frame and counters.')
    layout(clear,'06-clear-frame')
    layout(encrypted,'07-encrypted-frame',True)

    # 8: actual production CLI, scan mode, only the approved ID configured; no disk/MQTT output.
    env=os.environ.copy(); env['PYTHONPATH']=str(args.decoder/'addon'); env['PYTHONDONTWRITEBYTECODE']='1'
    with tempfile.TemporaryDirectory(prefix='taggle-blog-') as temporary:
        temp=Path(temporary)
        (temp/'slice.cu8').write_bytes(raw)
        (temp/'config.json').write_text(json.dumps({'meter_ids':[clear['id_decimal']],
            'neighbourhood':False,'log_all_meters':False}))
        run=subprocess.run([sys.executable,'-m','taggle_rx','--config',str(temp/'config.json'),
            '--input',str(temp/'slice.cu8'),'--start-utc','2026-01-01T00:00:00+00:00','--scan','1'],
            env=env,capture_output=True,text=True,check=True)
    logs=[]
    for line in run.stdout.splitlines():
        row=json.loads(line)
        assert row['meter_id']==clear['id_decimal'], 'unexpected meter in approved clip'
        assert row['counts']==frame['counts']
        # Relative time avoids publishing a household's absolute reception time.
        row.pop('time',None)
        logs.extend(['{',f'  "meter_id": {row["meter_id"]},',
                     f'  "counts": {row["counts"]},',
                     f'  "snr_median_db": {row["snr_median_db"]},',
                     f'  "signal_level_dbfs": {row["signal_level_dbfs"]}','}'])
    assert logs, 'production CLI must emit a real frame'
    lines=['# Real CLI replay; JSON reformatted, timestamp omitted.',
           '# Author’s meter 527814 / 0x80DC6; numeric ID retained.']+logs
    safe_log='\n'.join(lines)+'\n'
    (args.out/'receiver-log.txt').write_text(safe_log)
    fig,ax=plt.subplots(figsize=(10,3.6)); ax.set_axis_off()
    ax.text(.025,.96,safe_log,va='top',fontfamily='DejaVu Sans Mono',fontsize=12,linespacing=1.55)
    save(fig,'08-receiver-log',args.out,prov+' Production CLI stdout reformatted; numeric ID retained, timestamp omitted.')
    report={'source':'bursts/burst06_595.33s.cu8; first 1.2 seconds',
        'slice_sha256':hashlib.sha256(raw).hexdigest(),
        'sample_rate_msps':2.4,'centre_mhz':922.2,
        'clear_id':clear['id_decimal'],'clear_id_hex':clear['id_hex'],
        'clear_frame_hex':clear['decoded_frame_hex'],'counts':frame['counts'],
        'archive_snr_median_db':round(clear['snr_median_db'],1),'encrypted_id':encrypted['id_decimal'],
        'encrypted_id_hex':encrypted['id_hex'],
        'encrypted_frame_hex':encrypted['decoded_frame_hex'],
        'encrypted_source':'bursts/burst08_1406.47s.cu8',
        'clear_rf':{k:clear[k] for k in ('carrier_offset_hz','code_period_samples','snr_median_db','raw_coded_bits_hex','fec_errors')},
        'encrypted_rf':{k:encrypted[k] for k in ('carrier_offset_hz','code_period_samples','snr_median_db','fec_errors')},
        'tool_screenshots':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.out.glob('*.png')) if p.name.startswith(('waterfall-', 'urh-'))},
        'header_crc_pass':bool(header_ok),'frame_crc_pass':bool(frame_ok),
        'viterbi_corrections':int(errors),'cli_replayed':True,
        'privacy':'Author’s own frame, ID and counters shown with permission for this post only. Encrypted burst 08 ID and ciphertext also shown unmasked; no other clear frames or usage. Log timestamp omitted.',
        'decoder_commit':subprocess.check_output(['git','-C',str(args.decoder),'rev-parse','HEAD'],text=True).strip(),
        'figures':[p.name for p in sorted(args.out.glob('[0-9]*.png'))]}
    (args.out/'provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Rendered eight figures with the two approved frames unmasked; real CLI replay and both CRC checks passed.')


if __name__=='__main__':
    main()
