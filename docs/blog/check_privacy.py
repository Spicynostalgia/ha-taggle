#!/usr/bin/env python3
"""Grep publication text and matplotlib's rendered labels for private IDs.

The private full-frames.jsonl file is read only. Never print a matching ID.
Pass only publication outputs to --paths, including generated site assets and
make_figures.py. PNG pixels are checked through the corresponding .labels.json
source and their embedded textual metadata, rather than compressed image bytes.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', required=True, type=Path)
    parser.add_argument('--paths', nargs='+', required=True, type=Path)
    args = parser.parse_args()
    frames = [json.loads(line) for line in args.frames.open()]
    identifiers = {str(f['id_decimal']) for f in frames}
    hex_ids = {f['id_hex'].lower().removeprefix('0x').zfill(5) for f in frames}
    # Whole raw frames and coded dumps are also unacceptable publication output.
    forbidden = identifiers | hex_ids
    forbidden |= {str(f[key]).lower() for f in frames for key in
                  ('decoded_frame_hex','raw_coded_bits_hex','on_air_bits_hex')}
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
    assert len(label_files)==8, 'include the eight figure label-source files in this audit'
    print(f'PASS: {len(identifiers)} unique IDs from {len(frames)} real frames; '
          f'{len(texts)} text/metadata inputs, {images} PNGs, eight rendered-label sources; '
          'zero unmasked decimal/hex IDs or raw frame/bit dumps.')


if __name__=='__main__':
    main()
