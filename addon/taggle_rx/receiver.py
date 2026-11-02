"""Bounded streaming receiver for unsigned interleaved 8-bit IQ."""
import logging
import os
import queue
import selectors
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import numpy as np
from scipy import fft

from .dsss import Fold, predicted_template, recover_dsss
from .protocol import decode_frame, lfsr

RATE = 2_400_000
PERIOD = 2046.625
BLOCK = 120_000
LOG = logging.getLogger(__name__)


def iq(raw):
    a = np.frombuffer(raw, np.uint8).astype(np.float32) - 127.5
    return a[::2] + 1j*a[1::2]


class Detector:
    """Squared BPSK line screen, then a known-code cyclic power projection.

    No burst times, fitted templates, bits or per-meter priors are loaded.
    Circular projections tolerate an arbitrary symbol/code phase and BPSK signs.
    """
    def __init__(self, carrier=-205_000, radius=100_000, line_db=14., pn_ratio=12.):
        self.nfft = fft.next_fast_len(BLOCK)
        self.frequencies = fft.fftfreq(self.nfft, 1/RATE)
        self.selected = np.flatnonzero(abs(self.frequencies-2*carrier) < 2*radius)
        if not len(self.selected):
            raise ValueError('carrier search is outside the sampled band')
        self.window = np.hanning(BLOCK).astype(np.float32)
        self.code = (lfsr(0x1267) > 0).astype(np.uint8)
        self.line_db = line_db
        self.pn_ratio = pn_ratio

    def detect(self, raw):
        x = iq(raw); x -= x.mean()
        p = abs(fft.fft(x*x*self.window, self.nfft))**2
        band = p[self.selected]
        index = self.selected[np.argmax(band)]
        contrast = float(10*np.log10(max(float(p[index]), 1e-30) /
                                     max(float(np.median(band)), 1e-30)))
        if contrast < self.line_db:
            return None
        carrier = float(self.frequencies[index]/2)
        mixed = x*np.exp(-2j*np.pi*carrier*np.arange(len(x))/RATE)
        rows = Fold(mixed).rows(PERIOD)
        v = predicted_template(self.code, 2048, PERIOD, RATE, carrier, 0)
        projections = fft.ifft(fft.fft(rows, axis=1)*fft.fft(v).conj(), axis=1)
        powers = np.mean(abs(projections)**2, axis=0)
        ratio = float(powers.max()/max(float(np.median(powers)), 1e-30))
        if ratio < self.pn_ratio:
            return None
        noise = float(np.median(abs(x)**2)/np.log(2))
        return dict(carrier_offset_hz=carrier, square_line_db=contrast,
                    pn_peak_ratio=ratio,
                    level_dbfs=float(10*np.log10(max(float(np.mean(abs(x)**2)), 1e-30)/(2*127.5**2))),
                    snr_db=float(10*np.log10(max(ratio-1, 1e-12))),
                    snr_kind='PN cyclic peak/background power; screening statistic',
                    noise_power=noise)


def demodulate(raw, first, episode):
    x = iq(raw)
    lo = episode['first']-first
    hi = episode['last']-first
    # Train on the interior, avoiding partially filled detector windows.
    result = recover_dsss(x, episode['carrier_offset_hz'], PERIOD,
                          lo+.2*(hi-lo), hi-.2*(hi-lo), RATE)
    frame = decode_frame(result['bits'])
    a = int(result['first_sample']); b = int(result['last_sample'])
    quiet = np.r_[x[:max(1, a-round(.02*RATE))], x[min(len(x), b+round(.02*RATE)):]]
    noise = float(np.mean(abs(quiet-quiet.mean())**2)) if len(quiet) > 100 else episode['noise_power']
    total = float(np.mean(abs(x[max(0,a):min(len(x),b)])**2))
    frame.update(sample_offset=first+result['first_sample'],
                 snr_median_db=result['snr_median_db'], snr_p10_db=result['snr_p10_db'],
                 signal_level_dbfs=float(10*np.log10(max(total-noise, 1e-20)/(2*127.5**2))),
                 total_level_dbfs=float(10*np.log10(max(total, 1e-20)/(2*127.5**2))),
                 noise_dbfs=float(10*np.log10(max(noise, 1e-20)/(2*127.5**2))),
                 carrier_offset_hz=float(episode['carrier_offset_hz'] +
                     np.median(np.diff(result['phase']))*RATE/result['period_samples']/(2*np.pi)),
                 code_period_samples=result['period_samples'])
    return frame


class Receiver:
    def __init__(self, store, epoch, detector=None):
        self.store = store
        self.epoch = epoch
        self.detector = detector or Detector()
        self.samples = 0
        self.blocks = deque(maxlen=40)  # hard bound: 2 seconds / 9.6 MB
        self.pending = []
        self.detections = 0
        self.frames = 0
        self.overruns = 0
        self.decode_cpu_seconds = 0.

    def timestamp(self, sample):
        return self.epoch + timedelta(seconds=sample/RATE)

    def feed(self, raw):
        first = self.samples
        self.blocks.append((first, raw))
        self.samples += len(raw)//2
        hit = self.detector.detect(raw) if len(raw) == 2*BLOCK else None
        if hit:
            matching = next((p for p in self.pending if
                             first-p['last'] < .16*RATE and
                             abs(p['carrier_offset_hz']-hit['carrier_offset_hz']) < 500 and
                             first-p['first'] < .9*RATE), None)
            if matching:
                matching['last'] = self.samples
                if hit['pn_peak_ratio'] > matching['pn_peak_ratio']:
                    matching.update(hit)
            else:
                if len(self.pending) >= 8:
                    self.finish(self.pending[0])
                self.pending.append(dict(hit, first=first, last=self.samples))
                self.detections += 1
        for episode in list(self.pending):
            if self.samples-episode['last'] >= .2*RATE or self.samples-episode['first'] > 1.1*RATE:
                self.finish(episode)

    def finish(self, episode):
        self.pending.remove(episode)
        start = max(0, episode['first']-round(.18*RATE))
        end = min(self.samples, episode['last']+round(.18*RATE))
        pieces = [raw[2*max(0,start-pos):2*min(len(raw)//2,end-pos)]
                  for pos, raw in self.blocks if pos < end and pos+len(raw)//2 > start]
        actual_start = max(start, self.blocks[0][0])
        tic = time.process_time()
        try:
            frame = demodulate(b''.join(pieces), actual_start, episode)
            stamp = self.timestamp(frame['sample_offset'])
            self.store.frame(frame, stamp)
            self.frames += 1
        except ValueError as error:
            LOG.debug('undecodable PN detection: %s', error)
        finally:
            self.decode_cpu_seconds += time.process_time()-tic

    def flush(self):
        for episode in list(self.pending):
            self.finish(episode)

    def discontinuity(self, epoch):
        self.flush()
        self.blocks.clear()
        # The sample count remains cumulative; re-anchor the next sample to UTC.
        self.epoch = epoch-timedelta(seconds=self.samples/RATE)


class InputPump:
    """Drain the SDR while acquisition occupies the decoder for a few seconds."""
    def __init__(self, source, follow):
        self.source = source
        self.follow = follow
        self.items = queue.Queue(maxsize=256)  # 12.8 seconds / 61.4 MB maximum
        self.stop = threading.Event()
        self.backpressure_events = 0
        self.thread = threading.Thread(target=self.run, name='iq-reader', daemon=True)

    def put(self, item):
        while not self.stop.is_set():
            try:
                self.items.put(item, timeout=.2)
                return True
            except queue.Full:
                self.backpressure_events += 1
        return False

    def run(self):
        poll = selectors.DefaultSelector()
        streaming = not self.source.seekable()
        if streaming:
            os.set_blocking(self.source.fileno(), False)
            poll.register(self.source, selectors.EVENT_READ)
        pending = bytearray()
        at_eof = False
        origin = None
        try:
            while not self.stop.is_set():
                if streaming and not poll.select(timeout=.2):
                    continue
                try:
                    raw = os.read(self.source.fileno(), 2*BLOCK-len(pending))
                except BlockingIOError:
                    continue
                now = datetime.now(timezone.utc)
                if not raw:
                    if not at_eof:
                        if pending:
                            self.put(('data', bytes(pending), origin)); pending.clear()
                        self.put(('eof', None, now))
                        at_eof = True
                    if not self.follow:
                        break
                    self.stop.wait(.2)
                    continue
                at_eof = False
                if not pending:
                    origin = now-timedelta(seconds=len(raw)/(2*RATE))
                pending.extend(raw)
                if len(pending) == 2*BLOCK:
                    if not self.put(('data', bytes(pending), origin)):
                        break
                    pending.clear()
        except Exception as error:
            self.put(('error', error, None))
        finally:
            poll.close()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=1)

