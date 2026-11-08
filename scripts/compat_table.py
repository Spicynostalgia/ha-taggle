#!/usr/bin/env python3
"""Publish consenting, confirmed compatibility reports using only the stdlib."""

import html
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONSENT = 'I agree to list my council publicly in the compatibility tables.'
RESULTS = {'Unknown': 0, 'Not received': 1, 'IDs only': 2, 'Usage worked': 3}
METER_ID = re.compile(r'(?<!\d)\d(?:[ -]?\d){5,6}(?!\d)')
# Conservatively discard a whole line containing a numbered address. This also
# handles unit numbers, street abbreviations and suffixless addresses after a label.
ADDRESS = re.compile(
    r'\b\d+[a-z]?(?:\s*[/\-]\s*\d+[a-z]?)?\s+'
    r'(?:[\w\x27.-]+\s+){1,6}'
    r'(?:street|st|road|rd|avenue|ave|av|drive|dr|lane|ln|court|ct|crescent|cres|'
    r'place|pl|parade|pde|terrace|tce|highway|hwy|way|close|cl|circuit|cct|'
    r'grove|gr|boulevard|blvd|esplanade|esp)\b|'
    r'\b(?:address|unit|flat|lot|po\s+box)\s*[:#]?\s*\d+\b', re.I,
)


def scrub(value):
    """Remove sensitive text before it reaches any generated Markdown."""
    lines = []
    for line in str(value or '').splitlines():
        # Strip link destinations, HTML tags and images, retaining plain labels.
        line = html.unescape(line)
        line = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', line)
        line = re.sub(r'https?://\S+|<[^>]*>', '', line)
        # Formatting must not hide an address or split an ID into visible groups.
        visible = re.sub(r'[*_`~\\]', '', line)
        if ADDRESS.search(visible):
            continue
        line = METER_ID.sub('', line)
        if METER_ID.search(re.sub(r'[*_`~\\]', '', line)):
            continue
        lines.append(line)
    text = re.sub(r'\s+', ' ', ' '.join(lines))
    if ADDRESS.search(re.sub(r'[*_`~\\]', '', text)):
        return ''
    return METER_ID.sub('', text).strip(' ,;:-')[:160]


def cell(value):
    """Escape all user-controlled text; only generated report links are Markdown."""
    value = scrub(value) or 'Unknown'
    return ''.join(f'&#{ord(char)};' if char in r'\|`*_[]<>!&' else char for char in value)


def sections(body):
    fields = {}
    for section in re.split(r'^###\s+', body or '', flags=re.M)[1:]:
        heading, _, value = section.partition('\n')
        heading = heading.strip().casefold()
        # Ambiguous duplicate headings must not turn an unchecked consent into consent.
        if heading in fields:
            fields[heading] = ''
        else:
            fields[heading] = value.strip()
    return fields


def result(value):
    value = scrub(value).casefold()
    return {
        'usage worked': 'Usage worked', 'yes': 'Usage worked',
        'ids only': 'IDs only', 'id only': 'IDs only', 'not received': 'Not received',
    }.get(value, 'Unknown')


def frame(value):
    value = scrub(value).lower()
    return value.removesuffix('-byte').removesuffix(' bytes') if value in {
        '18', '21', '24', '18-byte', '21-byte', '24-byte', '18 bytes', '21 bytes', '24 bytes',
    } else 'Unknown'


def parse_issue(issue, repository):
    labels = {label['name'].casefold() for label in issue.get('labels', [])}
    if 'pull_request' in issue or not {'compatibility', 'confirmed'} <= labels:
        return None
    fields = sections(issue.get('body'))
    consent = fields.get('can we list your council publicly?', '')
    if not re.fullmatch(r'- \[[xX]\] ' + re.escape(CONSENT), consent):
        return None

    def field(*names):
        for name in names:
            value = fields.get(name.casefold(), '')
            if value and value != '_No response_':
                return scrub(value)
        return ''

    council = field('Council / utility', 'Council / LGA')
    state = field('State / country', 'State')
    if not council or not state:
        return None
    number = int(issue['number'])
    return {
        'council': council, 'state': state.upper(),
        'transmitter': field('Transmitter style'),
        'frames': frame(field('Frame length (bytes)')),
        'usage': result(field('Reception result', 'Did usage counts appear?')),
        'sdr': field('SDR model'), 'version': field('ha-taggle software version'),
        'report': f'[#{number}](https://github.com/{repository}/issues/{number})',
    }


def fetch_issues(repository, token):
    """The issues endpoint ANDs comma-separated labels; include closed reports too."""
    issues = []
    page = 1
    while True:
        query = urlencode({'labels': 'compatibility,confirmed', 'state': 'all',
                           'per_page': 100, 'page': page, 'sort': 'created', 'direction': 'asc'})
        request = Request(f'https://api.github.com/repos/{repository}/issues?{query}', headers={
            'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'ha-taggle-compat-table',
        })
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError('Expected a GitHub issues list')
        issues.extend(batch)
        if len(batch) < 100:
            return issues
        page += 1


def council_key(report):
    return re.sub(r'[^\w]', '', scrub(report['council']).casefold())


def safe_source(value):
    """Seed source URLs are trusted data, but still reject private-looking text."""
    value = str(value or '')
    parsed = urlsplit(value)
    if (parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.username
            or METER_ID.search(value) or ADDRESS.search(value)):
        raise ValueError('Seed source must be a public HTTP(S) URL without identifying details')
    return quote(value, safe=':/?#=&%+@~.-_')


def render(issues, seeds, repository):
    reports = []
    elsewhere = []
    for seed in seeds:
        clean = {key: scrub(seed.get(key)) for key in ('council', 'state', 'transmitter', 'sdr', 'version')}
        if not clean['council'] or not clean['state']:
            raise ValueError('Seed council and state are required')
        clean.update(state=clean['state'].upper(), frames=frame(seed.get('frames')),
                     usage=result(seed.get('usage')), report=cell(seed.get('report')))
        if seed.get('report') == 'reported elsewhere':
            clean['source_url'] = safe_source(seed.get('source_url'))
            elsewhere.append(clean)
        else:
            reports.append(clean)
    reports.extend(report for issue in issues if (report := parse_issue(issue, repository)))
    groups = {}
    for report in reports:
        groups.setdefault(council_key(report), []).append(report)
    rows = []
    for group in groups.values():
        # Keep fields together from the best report rather than imply that another
        # report's receiver/frame/version achieved the same result.
        best = max(group, key=lambda report: RESULTS[report['usage']])
        references = sorted({report['report'] for report in group})
        count = len(group)
        reference = ', '.join(references) + f' ({count} report{"s" if count != 1 else ""})'
        rows.append((best, reference))
    rows.sort(key=lambda row: (row[0]['state'].casefold(), row[0]['council'].casefold()))
    lines = [
        '| Council/LGA | State | Transmitter style | Frames (18/21/24) | Usage worked? | SDR | Version | Report |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for report, reference in rows:
        values = [cell(report[key]) for key in
                  ('council', 'state', 'transmitter', 'frames', 'usage', 'sdr', 'version')]
        lines.append('| ' + ' | '.join([*values, reference]) + ' |')
    lines.extend(['', 'Confirmed reports describe individual setups; council-wide compatibility is not guaranteed.'])
    if elsewhere:
        lines.extend(['', '### Reported by other projects', '',
                      'Not tested with ha-taggle; these reports do not count towards the badge.', '',
                      '| Council/LGA | State | Transmitter style | Source |', '| --- | --- | --- | --- |'])
        for report in sorted(elsewhere, key=lambda item: (item['state'], item['council'].casefold())):
            values = [cell(report[key]) for key in ('council', 'state', 'transmitter')]
            lines.append('| ' + ' | '.join([*values, f'[Source]({report["source_url"]})']) + ' |')
    return '\n'.join(lines) + '\n', len(groups)


def write_if_changed(path, content):
    if path.exists() and path.read_text(encoding='utf-8') == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return True


def generate(issues, repository, root=ROOT):
    seeds = json.loads((root / 'data/compat-seed.json').read_text(encoding='utf-8'))
    table, count = render(issues, seeds, repository)
    badge = {'schemaVersion': 1, 'label': 'councils reported', 'message': str(count),
             'color': 'brightgreen' if count else 'lightgrey'}
    outputs = {
        'docs/COMPATIBILITY.md': '# Where it works\n\n' + table,
        'docs/compat-badge.json': json.dumps(badge, indent=2) + '\n',
    }
    return [name for name, content in outputs.items() if write_if_changed(root / name, content)]


def main():
    repository = os.environ.get('GITHUB_REPOSITORY', '')
    token = os.environ.get('GITHUB_TOKEN', '')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) or not token:
        raise ValueError('Set GITHUB_REPOSITORY (owner/repo) and GITHUB_TOKEN')
    issues = fetch_issues(repository, token)
    changed = generate(issues, repository)
    print('Updated: ' + ', '.join(changed) if changed else 'Compatibility files unchanged.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, HTTPError, URLError):
        # Never echo response bodies, issue text, credentials or private paths.
        sys.exit('Compatibility update failed; check API access, seed data and README markers.')
