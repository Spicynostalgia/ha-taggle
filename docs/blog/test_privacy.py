#!/usr/bin/env python3
"""Exercise the publication audit against a private archive without printing IDs.

Usage: python docs/blog/test_privacy.py --frames /private/full-frames.jsonl
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', required=True, type=Path)
    args = parser.parse_args()
    frames = [json.loads(line) for line in args.frames.open()]
    approved = 'c080dc6e4f1ac0d301b49a1b48f1b48a5d00'
    rejected = set()
    for frame in frames:
        if frame['id_decimal'] != 527814:
            rejected.add(str(frame['id_decimal']))
            hex_id = frame['id_hex'].removeprefix('0x')
            rejected.update((hex_id.lower(), hex_id.upper(), '0x'+hex_id))
        if frame['decoded_frame_hex'].lower() != approved:
            rejected.add(frame['decoded_frame_hex'])
        rejected.update(frame[key] for key in ('raw_coded_bits_hex', 'on_air_bits_hex'))
    with tempfile.TemporaryDirectory(prefix='taggle-privacy-test-') as temporary:
        root = Path(temporary)
        for index in range(8):
            (root/f'{index}.labels.json').write_text('[]')
        probe = root/'probe.txt'
        def check(value, expected):
            probe.write_text(value)
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('check_privacy.py')),
                                     '--frames', str(args.frames.resolve()), '--paths', str(root)],
                                    capture_output=True, text=True)
            assert (result.returncode == 0) == expected, 'privacy regression (values withheld)'
        check('527814 / 0x80DC6 / 80dc6 / '+approved.upper(), True)
        for value in rejected:
            check(value, False)
        probe.write_text('')
        # Also prove that rendered labels and PNG metadata cannot bypass the audit.
        private = str(next(frame['id_decimal'] for frame in frames if frame['id_decimal'] != 527814))
        (root/'0.labels.json').write_text(json.dumps([private]))
        check('', False)
        (root/'0.labels.json').write_text('[]')
        from PIL.PngImagePlugin import PngInfo
        metadata = PngInfo()
        metadata.add_text('Description', private)
        Image.new('RGB', (1, 1)).save(root/'probe.png', pnginfo=metadata)
        check('', False)
    print(f'PASS: approved ID/frame accepted; {len(rejected)} private ID/frame/bit-dump probes, '
          'rendered labels and PNG metadata rejected. No private values printed.')


if __name__ == '__main__':
    main()
