#!/usr/bin/env python3
"""Replace the owner placeholder in all distributable text files."""
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER = 'GITHUB' + '_OWNER'


def set_owner(owner, root=ROOT):
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?', owner):
        raise ValueError('Owner must be a GitHub user or organization name, not a URL')
    owner = owner.lower()
    listing = subprocess.check_output(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=root)
    changed = []
    for name in sorted(set(listing.split(b'\0')) - {b''}):
        path = root / name.decode()
        if not path.is_file() or path.is_symlink():
            continue
        try:
            content = path.read_text()
        except UnicodeDecodeError:
            continue
        if PLACEHOLDER in content:
            path.write_text(content.replace(PLACEHOLDER, owner))
            changed.append(path.relative_to(root))
    return changed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('owner', help='GitHub user or organization that will publish the images')
    args = parser.parse_args()
    try:
        changed = set_owner(args.owner)
    except ValueError as error:
        parser.exit(1, f'{error}\n')
    for path in changed:
        print(path)
    print(f'Updated {len(changed)} files.')
