import numpy as np
import pytest
from scipy import fft
from taggle_rx.coding import convolution_decode_viterbi, crc_bits
from taggle_rx.protocol import decode_frame, lfsr

from .synthetic import air, frame_bytes


@pytest.mark.parametrize('size', [18, 21, 24])
def test_synthetic_frame(size):
    result = decode_frame(air(frame_bytes(size=size)))
    assert result['meter_id'] == 123456
    assert result['format_bytes'] == size
    assert result['encrypted'] == (size == 24)
    assert ('counts' in result) == (size != 24)
    assert not any('hex' in k for k in result)


def test_fec_repairs_and_independent_impulse_vector():
    bits = air(frame_bytes())
    bits[240] ^= 1
    assert decode_frame(bits)['fec_errors'] == 1
    impulse = np.array(list(map(int, '110111110010110000')), np.uint8)
    impulse[5] ^= 1
    decoded, errors = convolution_decode_viterbi(impulse)
    assert list(decoded) == [1, 0, 0, 0, 0, 0, 0, 0, 0]
    assert errors == 1


def test_crc_reference_and_corruption():
    assert crc_bits(np.unpackbits(np.frombuffer(b'123456789', np.uint8)), 8, 7) == 0xf4
    for bit in range(17 * 8):
        data = bytearray(frame_bytes())
        data[bit // 8] ^= 1 << (7 - bit % 8)
        with pytest.raises(ValueError):
            decode_frame(air(data))


def test_header_check_is_independent():
    data = bytearray(frame_bytes())
    data[1] ^= 0x10
    bits = np.unpackbits(np.frombuffer(data, np.uint8))
    data[-2] = crc_bits(bits[8:-16], 8, 7)
    with pytest.raises(ValueError, match='header CRC'):
        decode_frame(air(data))


def test_pn_period_balance_autocorrelation_and_forward_recurrence():
    code = lfsr()
    assert len(code) == 4095 and sum(code.astype(int)) == -1
    autocorrelation = fft.ifft(abs(fft.fft(code))**2).real
    np.testing.assert_allclose(autocorrelation[1:], -1, atol=1e-8)
    bits = (1-code) // 2
    for n in range(4095-12):
        assert bits[n+12] == bits[n+9] ^ bits[n+6] ^ bits[n+5] ^ bits[n+2] ^ bits[n+1] ^ bits[n]


@pytest.mark.parametrize('length', [0, 100, 391, 393, 487, 489])
def test_truncation(length):
    with pytest.raises(ValueError):
        decode_frame(np.zeros(length, np.uint8))


def test_excessive_fec_errors_are_rejected():
    bits = air(frame_bytes())
    rng = np.random.default_rng(97)
    bits[104:] ^= rng.integers(0, 2, len(bits)-104, dtype=np.uint8)
    with pytest.raises(ValueError, match='FEC'):
        decode_frame(bits)
