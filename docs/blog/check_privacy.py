#!/usr/bin/env python3
"""Grep publication text and matplotlib's rendered labels for private IDs.

The private full-frames.jsonl file is read only. Never print a matching ID.
Pass only publication outputs to --paths, including generated site assets and
make_figures.py. PNG pixels are checked through the corresponding .labels.json
source and their embedded textual metadata, rather than compressed image bytes.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

# Permission is scoped to these exact captures, not every frame from either ID.
APPROVED_FRAMES = {
    527814: 'c080dc6e4f1ac0d301b49a1b48f1b48a5d00',
    766910: 'c0bb3beaf5fa2ee84a43cfd6713761ad97925f7b24d16a00',
}


def approved(frame):
    return APPROVED_FRAMES.get(frame['id_decimal']) == frame['decoded_frame_hex'].lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', required=True, type=Path)
    parser.add_argument('--paths', nargs='+', required=True, type=Path)
    args = parser.parse_args()
    frames = [json.loads(line) for line in args.frames.open()]
    private_frames = [f for f in frames if f['id_decimal'] not in APPROVED_FRAMES]
    identifiers = {str(f['id_decimal']) for f in private_frames}
    hex_ids = {f['id_hex'].lower().removeprefix('0x').zfill(5) for f in private_frames}
    forbidden = identifiers | hex_ids
    # Full coded/on-air bits are visible in the two unblurred URH screenshots.
    # All other captures remain private, including other frames from allowed IDs.
    forbidden |= {str(f[key]).lower() for f in frames if not approved(f) for key in
                  ('decoded_frame_hex', 'raw_coded_bits_hex', 'on_air_bits_hex')}
    forbidden |= {f['opaque_body_hex'].lower() for f in frames
                  if not approved(f) and f.get('opaque_body_hex')}
    files=set()
    for path in args.paths:
        files.update(p for p in path.rglob('*') if p.is_file()) if path.is_dir() else files.add(path)
    texts={}
    images=0
    for path in sorted(files):
        if path.suffix == '.png':
            images+=1
            with Image.open(path) as image:
                texts[str(path)] = json.dumps(image.info,ensure_ascii=False)
            # Copies on the wiki/site must match the audited PNGs, checked by
            # publication parity verification; their labels stay in main repo.
        elif path.suffix in {'.py','.md','.html','.css','.js','.json','.txt','.xml'}:
            texts[str(path)] = path.read_text()
    failures=[]
    # Use real fixed-string grep; keep its pattern file and matches private.
    with tempfile.TemporaryDirectory(prefix='taggle-privacy-') as temporary:
        patterns=Path(temporary)/'patterns'
        patterns.write_text('\n'.join(sorted(forbidden))+'\n')
        for path, content in texts.items():
            result=subprocess.run(['rg','--ignore-case','--fixed-strings','--quiet',
                                   '--file',str(patterns),'-'],input=content,text=True)
            if result.returncode==0:
                failures.append(path)
            elif result.returncode!=1:
                raise RuntimeError('privacy grep did not complete')
    if failures:
        raise SystemExit('FAIL: private identifiers or payload found in: '+', '.join(failures))
    label_files=[p for p in files if p.name.endswith('.labels.json')]
    assert len(label_files)==11, 'include all eleven radio and calibration figure label-source files in this audit'
    print(f'PASS: {len(identifiers)} private IDs from {len(frames)} real frames; '
          f'{len(texts)} text/metadata inputs, {images} PNGs, {len(label_files)} rendered-label sources; '
          'only IDs 527814/0x80DC6 and 766910/0xBB3BE plus their two selected frames allowed; '
          'zero private ID or frame/bit-dump matches.')


if __name__=='__main__':
    main()
