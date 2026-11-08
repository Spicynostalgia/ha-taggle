import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('compat_table', ROOT / 'scripts/compat_table.py')
compat = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compat)
REPO = 'example/ha-taggle'


@pytest.fixture
def body():
    return f'''### Council / utility

Example Regional Council

### State / country

NSW

### Town/suburb (optional, no street address)

Private suburb

### Can we list your council publicly?

- [X] {compat.CONSENT}

### Transmitter style

cable tag

### Transmitter photo (optional)

![photo](https://example.org/private-photo.png)

### Frame length (bytes)

21

### Reception result

IDs only

### SDR model

RTL-SDR Blog V4

### ha-taggle software version

0.3.0
'''


@pytest.fixture
def issue(body):
    return {'number': 42, 'body': body, 'state': 'closed',
            'labels': [{'name': 'compatibility'}, {'name': 'confirmed'}]}


@pytest.fixture
def seeds():
    return json.loads((ROOT / 'data/compat-seed.json').read_text())


def test_valid_closed_report_and_seed(issue, seeds):
    table, count = compat.render([issue], seeds, REPO)
    assert count == 2
    assert '| Example Regional Council | NSW | cable tag | 21 | IDs only | RTL-SDR Blog V4 | 0.3.0 |' in table
    assert '[#42](https://github.com/example/ha-taggle/issues/42)' in table
    assert '| Gladstone Regional Council | QLD | cable-connected tube | 18 | Usage worked |' in table
    assert '0.2.1 | maintainer test (1 report)' in table
    assert table.index('Example Regional Council') < table.index('Gladstone Regional Council')
    assert 'Private suburb' not in table
    assert 'private-photo' not in table


def test_missing_optional_fields_are_unknown(issue):
    issue['body'] = issue['body'].split('### Transmitter style')[0]
    report = compat.parse_issue(issue, REPO)
    assert report['frames'] == report['usage'] == 'Unknown'
    table, count = compat.render([issue], [], REPO)
    assert count == 1
    assert '| Unknown | Unknown | Unknown | Unknown | Unknown |' in table


@pytest.mark.parametrize('heading', ['Council / utility', 'State / country'])
def test_missing_required_fields_excluded(issue, heading):
    issue['body'] = issue['body'].replace(f'### {heading}', '### unrelated')
    assert compat.parse_issue(issue, REPO) is None


@pytest.mark.parametrize('consent', [
    '', f'- [ ] {compat.CONSENT}', '- [x] a different promise',
    f'- [x] {compat.CONSENT}\n\n### Can we list your council publicly?\n\n- [ ] {compat.CONSENT}',
])
def test_not_public_excluded(issue, consent):
    issue['body'] = issue['body'].replace(f'- [X] {compat.CONSENT}', consent)
    table, count = compat.render([issue], [], REPO)
    assert compat.parse_issue(issue, REPO) is None
    assert count == 0
    assert 'Example Regional Council' not in table


@pytest.mark.parametrize('missing', ['compatibility', 'confirmed'])
def test_requires_both_labels(issue, missing):
    issue['labels'] = [label for label in issue['labels'] if label['name'] != missing]
    assert compat.parse_issue(issue, REPO) is None


def test_pull_request_excluded(issue):
    issue['pull_request'] = {}
    assert compat.parse_issue(issue, REPO) is None


def test_duplicates_choose_best_complete_report_and_count(issue, body):
    better = dict(issue, number=43, body=body.replace('IDs only', 'Usage worked')
                  .replace('21\n', '24\n').replace('RTL-SDR Blog V4', 'Different receiver')
                  .replace('Example Regional Council', 'example regional council'))
    worse = dict(issue, number=44, body=body.replace('IDs only', 'Not received'))
    table, count = compat.render([worse, issue, better], [], REPO)
    assert count == 1
    assert table.count('| NSW |') == 1
    assert '| 24 | Usage worked | Different receiver |' in table
    assert '(3 reports)' in table
    assert all(f'[#{number}]' in table for number in (42, 43, 44))
    assert compat.render([issue, worse], [], REPO)[0].count('| 21 | IDs only |') == 1


def test_duplicate_seed_stays_in_references(issue, body, seeds):
    issue['body'] = body.replace('Example Regional Council', 'Gladstone Regional Council')
    table, count = compat.render([issue], seeds, REPO)
    assert count == 1
    assert 'maintainer test' in table and '[#42]' in table and '(2 reports)' in table
    assert '| QLD | cable-connected tube | 18 | Usage worked |' in table


@pytest.mark.parametrize('sensitive', [
    '123456', '1234567', '123-456', '123 4567', '1234-567', '12 34 56',
    '12 Example Street', '12A Example St.', '4/12 Example Road', '12-14 Example Rd',
    'Unit 4, Example Building', 'Address: 12 Example', 'PO Box 44',
    '99 Example Circuit', '&#49;23456',
])
def test_sensitive_free_text_never_rendered(issue, body, sensitive):
    issue['body'] = body.replace('cable tag', f'cable tag\n{sensitive}')
    issue['body'] = issue['body'].replace('RTL-SDR Blog V4', f'RTL-SDR Blog V4\n{sensitive}')
    issue['body'] = issue['body'].replace('0.3.0', f'0.3.0\n{sensitive}')
    table, count = compat.render([issue], [], REPO)
    assert count == 1
    assert sensitive not in table
    assert '123456' not in table
    assert 'Example Street' not in table
    assert 'RTL-SDR Blog V4' in table


@pytest.mark.parametrize('private', [
    '12 **Example** Street', '12 Example\nStreet', '123\n456', '123`456',
])
def test_formatting_and_line_breaks_do_not_hide_private_text(private):
    assert compat.scrub(private) == ''


def test_sensitive_council_is_excluded(issue, body):
    issue['body'] = body.replace('Example Regional Council', '12 Example Street')
    assert compat.parse_issue(issue, REPO) is None


def test_markdown_cannot_inject_links_or_rows(issue, body):
    issue['body'] = body.replace('RTL-SDR Blog V4',
                                 '[receiver](https://example.org/123456) | <img src=x> **fake**')
    table, _ = compat.render([issue], [], REPO)
    assert 'example.org' not in table
    assert '<img' not in table
    assert '&#124;' in table and '&#42;' in table
    assert all(line.count('|') == 9 for line in table.splitlines() if line.startswith('|'))


def test_legacy_form_yes_supported_but_no_is_unknown(issue, body):
    issue['body'] = body.replace('Reception result', 'Did usage counts appear?').replace('IDs only', 'Yes')
    assert compat.parse_issue(issue, REPO)['usage'] == 'Usage worked'
    issue['body'] = issue['body'].replace('\nYes\n', '\nNo\n')
    assert compat.parse_issue(issue, REPO)['usage'] == 'Unknown'


def test_elsewhere_sources_separate_and_not_counted(seeds):
    source = {'council': 'Other Council', 'state': 'VIC', 'transmitter': 'clip-on',
              'report': 'reported elsewhere', 'source_url': 'https://example.org/project/report'}
    table, count = compat.render([], [*seeds, source], REPO)
    assert count == 1
    main, other = table.split('### Reported by other projects')
    assert 'Other Council' not in main
    assert 'Not tested with ha-taggle' in other
    assert '[Source](https://example.org/project/report)' in other


@pytest.mark.parametrize('source', ['javascript:alert(1)', 'https://example.org/123456', ''])
def test_invalid_seed_source_rejected(source):
    with pytest.raises(ValueError):
        compat.safe_source(source)


def test_generate_idempotent_and_badge_counts_councils(tmp_path, issue, seeds):
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/compat-seed.json').write_text(json.dumps(seeds))
    readme = 'Quick start\nSee docs/COMPATIBILITY.md for reports.\n'
    (tmp_path / 'README.md').write_text(readme)
    readme_mtime = (tmp_path / 'README.md').stat().st_mtime_ns
    changed = compat.generate([issue], REPO, tmp_path)
    assert changed == ['docs/COMPATIBILITY.md', 'docs/compat-badge.json']
    times = {name: (tmp_path / name).stat().st_mtime_ns for name in changed}
    assert compat.generate([issue], REPO, tmp_path) == []
    assert times == {name: (tmp_path / name).stat().st_mtime_ns for name in changed}
    badge = json.loads((tmp_path / 'docs/compat-badge.json').read_text())
    assert badge == {'schemaVersion': 1, 'label': 'councils reported', 'message': '2', 'color': 'brightgreen'}
    assert 'Example Regional Council' in (tmp_path / 'docs/COMPATIBILITY.md').read_text()
    compat.generate([], REPO, tmp_path)
    assert 'Example Regional Council' not in (tmp_path / 'docs/COMPATIBILITY.md').read_text()
    assert (tmp_path / 'README.md').read_text() == readme
    assert (tmp_path / 'README.md').stat().st_mtime_ns == readme_mtime


def test_api_pagination_and_required_request_parameters(monkeypatch, issue):
    requests = []

    def respond(request, timeout):
        requests.append(request)
        assert timeout == 30
        assert request.get_header('Authorization') == 'Bearer fake-token'
        query = parse_qs(urlsplit(request.full_url).query)
        assert query['labels'] == ['compatibility,confirmed']
        assert query['state'] == ['all']
        assert query['per_page'] == ['100']
        batch = [dict(issue, number=n) for n in range(1, 101)] if query['page'] == ['1'] else [issue]
        return io.BytesIO(json.dumps(batch).encode())

    monkeypatch.setattr(compat, 'urlopen', respond)
    assert len(compat.fetch_issues(REPO, 'fake-token')) == 101
    assert len(requests) == 2


def test_api_failure_does_not_generate_files(monkeypatch):
    monkeypatch.setenv('GITHUB_REPOSITORY', REPO)
    monkeypatch.setenv('GITHUB_TOKEN', 'fake-token')

    def fail(*args, **kwargs):
        raise HTTPError('https://api.github.com', 403, 'Forbidden', {}, None)

    def unexpected(*args):
        pytest.fail('Must not generate files after a failed fetch')

    monkeypatch.setattr(compat, 'urlopen', fail)
    monkeypatch.setattr(compat, 'generate', unexpected)
    with pytest.raises(HTTPError):
        compat.main()


def test_form_labels_and_consent_match_parser():
    form = yaml.safe_load((ROOT / '.github/ISSUE_TEMPLATE/compatibility.yml').read_text())
    assert form['labels'] == ['compatibility']
    fields = {field['id']: field for field in form['body'] if 'id' in field}
    consent = fields['public-consent']['attributes']
    assert consent['label'].casefold() == 'can we list your council publicly?'
    assert consent['options'] == [{'label': compat.CONSENT, 'required': True}]
    assert fields['usage']['attributes']['options'][:3] == ['Usage worked', 'IDs only', 'Not received']
    assert fields['town']['attributes']['label'] == 'Town/suburb (optional, no street address)'
