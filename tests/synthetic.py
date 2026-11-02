"""Self-contained fixtures generated from public recurrence and coding rules."""
import numpy as np
from scipy import signal
from taggle_rx.coding import convolution_encode, crc_bits
from taggle_rx.protocol import lfsr
from taggle_rx.receiver import PERIOD, RATE


def frame_bytes(identifier=123456, size=18, sequence=7, counts=(120, 110, 104), flags=(1, 1, 1)):
    # The ID and its CRC occupy 28 bits, hence the nibble-aligned layout.
    text = 'c0' + f'{identifier:05x}' + '00' + 'f' + '0' + f'{sequence:02x}' + '0000'
    text += ''.join(f'{flag:x}{value:04x}' for flag, value in zip(flags, counts))
    text += '00' * (size - 18) + '0000'
    bits = np.unpackbits(np.frombuffer(bytes.fromhex(text), np.uint8))
    # Solve the 8-bit header residue, keeping the independent full-frame CRC.
    for check in range(256):
        bits[28:36] = np.unpackbits(np.array([check], np.uint8))
        if crc_bits(bits[8:36], 8, 7) == 0:
            break
    data = bytearray(np.packbits(bits).tobytes())
    data[-2] = crc_bits(bits[8:-16], 8, 7)
    return bytes(data)


def air(data):
    return np.r_[np.zeros(104, np.uint8), convolution_encode(
        np.unpackbits(np.frombuffer(data, np.uint8)))]


def burst(data=None, *, seed=73, carrier=-205_123.0, period=PERIOD, amplitude=28, noise=1.6):
    """Generate at 4x ADC rate and low-pass BEFORE decimating to avoid aliasing.

    This is a receive-test fixture, with no radio/transmit support.
    """
    bits = air(data or frame_bytes())
    oversample = 4
    margin = round(.18 * RATE)
    total = 2 * margin + int(np.ceil(len(bits) * period))
    code = lfsr()
    output = np.empty(total, np.complex64)
    # Bounded blocks, with FIR margins, reproduce a continuous high-rate waveform.
    for start in range(0, total, 120_000):
        stop = min(total, start + 120_000)
        pad = 64
        t = np.arange((start-pad)*oversample, (stop+pad)*oversample, dtype=np.float64) / oversample
        position = (t-margin-.37) / period
        symbol = np.floor(position).astype(np.int64)
        valid = (symbol >= 0) & (symbol < len(bits))
        wave = np.zeros(len(t), np.complex64)
        chip = np.floor(position[valid] * 4095).astype(np.int64) % 4095
        signs = 1 - 2 * bits[symbol[valid]].astype(np.float32)
        phase = 2*np.pi*(carrier*t[valid]/RATE + .6*(t[valid]/RATE)**2) + .43
        wave[valid] = amplitude * code[chip] * signs * np.exp(1j*phase)
        filtered = signal.resample_poly(wave, 1, oversample, window=('kaiser', 9.0))
        output[start:stop] = filtered[pad:pad+stop-start]
    rng = np.random.default_rng(seed)
    output += noise * (rng.normal(size=total) + 1j*rng.normal(size=total))
    return np.clip(np.column_stack((output.real, output.imag)) + 127.5, 0, 255).round().astype(np.uint8).tobytes()
