from datetime import datetime, timezone

import numpy as np
import pytest
from taggle_rx.protocol import decode_frame
from taggle_rx.receiver import BLOCK, Detector, InputPump, Receiver

from .synthetic import burst, frame_bytes


@pytest.mark.parametrize('size', [18, 21, 24])
def test_full_generated_iq_through_streaming_receiver(size):
    frames = []

    class Sink:
        def frame(self, frame, stamp):
            frames.append(frame)

    raw = burst(frame_bytes(size=size))
    rx = Receiver(Sink(), datetime(2026, 1, 1, tzinfo=timezone.utc))
    for start in range(0, len(raw), 2*BLOCK):
        rx.feed(raw[start:start+2*BLOCK])
    rx.flush()
    assert len(frames) == 1
    assert frames[0]['meter_id'] == 123456
    assert frames[0]['format_bytes'] == size
    assert frames[0]['fec_errors'] == 0
    assert frames[0]['snr_median_db'] > 5
    assert len(rx.blocks) <= 40


def test_noise_and_unrelated_carrier_rejected():
    rng = np.random.default_rng(29)
    detector = Detector()
    for tone in (0, 15):
        t = np.arange(BLOCK)
        z = rng.normal(size=BLOCK) + 1j*rng.normal(size=BLOCK)
        z += tone * np.exp(-2j*np.pi*210000*t/2400000)
        raw = np.clip(np.column_stack((z.real, z.imag))+127.5, 0, 255).astype(np.uint8).tobytes()
        assert detector.detect(raw) is None


def test_invalid_preamble():
    from .synthetic import air
    bits = air(frame_bytes())
    bits[:104] = 1
    with pytest.raises(ValueError, match='preamble'):
        decode_frame(bits)


def test_input_pump_short_reads_and_eof(tmp_path):
    path = tmp_path / 'synthetic.bin'
    data = bytes(range(256)) * 1000 + b'xy'
    path.write_bytes(data)
    with path.open('rb', buffering=0) as source:
        pump = InputPump(source, False)
        pump.thread.start()
        received = bytearray()
        while True:
            kind, raw, _ = pump.items.get(timeout=3)
            if kind == 'eof':
                break
            assert kind == 'data'
            received.extend(raw)
        pump.close()
    assert received == data
