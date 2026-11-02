"""Taggle framing. Opaque bodies are never interpreted or exposed."""
import numpy as np

from .coding import convolution_decode_exact, convolution_decode_viterbi, crc_bits


def lfsr(polynomial=0x1267, state=1, count=4095):
    """Forward recurrence; bit i of state is s[n+i], 1 maps to -1."""
    degree = polynomial.bit_length() - 1
    taps = polynomial ^ (1 << degree)
    result = np.empty(count, np.int8)
    for i in range(count):
        result[i] = 1 - 2 * (state & 1)
        state = (state >> 1) | (((state & taps).bit_count() & 1) << (degree - 1))
    return result


def decode_frame(bits):
    bits = np.asarray(bits, np.uint8)
    if len(bits) not in (392, 440, 488) or np.any(bits > 1):
        raise ValueError('unsupported/truncated symbol count or invalid bits')
    if np.count_nonzero(bits[:104]) > 4:
        raise ValueError('constant preamble failed')
    plain, violations, terminal = convolution_decode_exact(bits[104:])
    errors = 0
    if violations or terminal:
        plain, errors = convolution_decode_viterbi(bits[104:])
        if errors > 12:
            raise ValueError('excessive FEC corrections')
    data = np.packbits(plain).tobytes()
    if data[0] != 0xc0 or data[-1] != 0:
        raise ValueError('sync/tail failed')
    if crc_bits(plain[8:36], 8, 7) != 0:
        raise ValueError('ID header CRC failed')
    if crc_bits(plain[8:-16], 8, 7) != data[-2]:
        raise ValueError('frame CRC failed')
    text = data.hex()
    result = {'meter_id': int(text[2:7], 16), 'format_bytes': len(data),
              'fec_errors': errors, 'encrypted': len(data) == 24}
    if len(data) in (18, 21):
        result.update(sequence=int(text[11:13], 16),
                      counts=[int(text[n+1:n+5], 16) for n in (17, 22, 27)],
                      flags=[int(text[n], 16) for n in (17, 22, 27)])
    return result
