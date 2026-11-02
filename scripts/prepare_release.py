#!/usr/bin/env python3
"""Validate release versions and extract the matching changelog section."""
import argparse
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def check_compose_version(version, root=ROOT):
    compose = yaml.safe_load((root / 'docker-compose.yml').read_text())
    image = compose['services']['taggle']['image']
    if not image.endswith(f'/ha-taggle:{version}'):
        raise ValueError(f'v{version} does not match docker-compose.yml image {image}')


def prepare(tag, root=ROOT):
    if not re.fullmatch(r'v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)', tag):
        raise ValueError('Release tag must be vMAJOR.MINOR.PATCH')
    version = tag[1:]
    addon = yaml.safe_load((root / 'addon/config.yaml').read_text())
    versions = {'addon/config.yaml': addon['version']}
    for name in ('pyproject.toml', 'addon/pyproject.toml'):
        versions[name] = tomllib.loads((root / name).read_text())['project']['version']
    for name, actual in versions.items():
        if actual != version:
            raise ValueError(f'{tag} does not match {name} version {actual}')
    changelog = (root / 'CHANGELOG.md').read_text()
    section = re.search(rf'^## {re.escape(version)}\s*\n(.*?)(?=^## |\Z)', changelog, re.M | re.S)
    if not section or not section[1].strip():
        raise ValueError(f'No CHANGELOG.md section for {version}')
    return section[1].strip() + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag')
    parser.add_argument('--notes', type=Path, required=True)
    args = parser.parse_args()
    try:
        notes = prepare(args.tag)
        check_compose_version(args.tag[1:])
    except ValueError as error:
        parser.exit(1, f'{error}\n')
    args.notes.write_text(notes)
