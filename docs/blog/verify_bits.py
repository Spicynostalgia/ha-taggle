#!/usr/bin/env python3
"""Verify the two approved captured bitstreams without private IQ or an archive.

Requires NumPy and the receiver source. This checks bits to fields only; it
cannot establish RF acquisition, carrier/timing fits, or screenshot provenance.
"""
import argparse
import sys
from pathlib import Path

# Exact archive on-air bits, packed MSB-first; only these captures are approved.
# The final byte may contain packing padding, excluded using the symbol count.
EXAMPLES = [
    {
        'meter_id': 527814,
        'symbols': 392,
        'on_air_bits_hex': '00000000000000000000000000e8e7df2ceb736ddce2ed6ade8627eb953e73ad2567826d6d2564ca6add2564feea9c2bb0',
        'decoded_frame_hex': 'c080dc6e4f1ac0d301b49a1b48f1b48a5d00',
    },
    {
        'meter_id': 766910,
        'symbols': 488,
        'on_air_bits_hex': '00000000000000000000000000e8e7d173dc2f37b7f89d210ba3d7300adb19e905667182d1b08602070f4a6e8587d9292d7691e0e4dfb5e098f65b1ec0',
        'decoded_frame_hex': 'c0bb3beaf5fa2ee84a43cfd6713761ad97925f7b24d16a00',
    },
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decoder', type=Path, default=Path(__file__).resolve().parents[2],
                        help='receiver repository (defaults to this checkout)')
    args = parser.parse_args()
    sys.path.insert(0, str(args.decoder / 'addon'))
    import numpy as np
    from taggle_rx.coding import convolution_decode_viterbi, convolution_encode, crc_bits
    from taggle_rx.protocol import decode_frame

    for example in EXAMPLES:
        bits = np.unpackbits(np.frombuffer(bytes.fromhex(example['on_air_bits_hex']),
                                         dtype=np.uint8))[:example['symbols']]
        frame = decode_frame(bits)
        plain, errors = convolution_decode_viterbi(bits[104:])
        data = np.packbits(plain).tobytes()
        assert data.hex() == example['decoded_frame_hex']
        assert errors == frame['fec_errors'] == 0
        assert np.array_equal(convolution_encode(plain), bits[104:])
        assert np.count_nonzero(bits[:104]) <= 4
        assert data[0] == 0xC0 and data[-1] == 0
        assert crc_bits(plain[8:36], 8, 7) == 0
        assert crc_bits(plain[8:28], 8, 7) == int(data.hex()[7:9], 16)
        assert crc_bits(plain[8:-16], 8, 7) == data[-2]
        assert frame['meter_id'] == example['meter_id']
        if example['meter_id'] == 527814:
            assert not frame['encrypted']
            assert frame['sequence'] == 172 and frame['flags'] == [1, 1, 1]
            assert frame['counts'] == [46234, 46223, 46218]
            deltas = [(a - b) % 65536 for a, b in zip(frame['counts'], frame['counts'][1:])]
            assert deltas == [11, 5]
            assert [delta * 5 for delta in deltas] == [55, 25]
        else:
            assert frame['encrypted'] and 'counts' not in frame
        print(f"PASS: {example['meter_id']}, {len(data)} bytes; exact re-encoding, "
              "zero Viterbi corrections, preamble/sync/tail and both CRCs.")
    print('PASS: clear counters and deltas; opaque body not interpreted. RF not tested.')


if __name__ == '__main__':
    main()
