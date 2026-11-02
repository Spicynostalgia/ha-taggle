#!/usr/bin/env python3
"""Check distributable files; optional private deny patterns stay outside the repo."""
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(deny_file=None):
    listing = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT)
    files = sorted({ROOT / name.decode() for name in listing.split(b'\0') if name})
    # Generic guards. The release audit may additionally supply private literal patterns.
    guards = [r'/(?:home|Users|volume\d?)/[A-Za-z0-9._-]+/',
              r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
              r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
              r'\b(?:ghp|gho|github_pat)_[A-Za-z0-9_]{20,}\b']
    if deny_file:
        guards.extend(re.escape(line) for line in Path(deny_file).read_text().splitlines() if line)
    patterns = [re.compile(pattern, re.I) for pattern in guards]
    failures = []
    for path in files:
        if not path.is_file():
            continue
        if path.suffix.lower() in {'.cu8', '.iq', '.npy', '.npz', '.pcap', '.jsonl'}:
            failures.append(f'{path.relative_to(ROOT)}: forbidden data artifact')
            continue
        content = path.read_text()
        if any(pattern.search(content) for pattern in patterns):
            failures.append(f'{path.relative_to(ROOT)}: privacy guard matched')
    source, bundle = ROOT / 'card/taggle-card.js', ROOT / 'dist/taggle-card.js'
    if source.read_bytes() != bundle.read_bytes():
        failures.append('card distribution differs from source')
    print(f'Scanned {len(files)} distributable paths; {len(failures)} failures.')
    for failure in failures:
        print(failure)
    return int(bool(failures))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deny-file', help='private newline-separated literals; do not commit this file')
    raise SystemExit(check(parser.parse_args().deny_file))
