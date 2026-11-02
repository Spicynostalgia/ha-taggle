import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f'scripts/{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prepare = load_script('prepare_release').prepare
set_owner_module = load_script('set_owner')
check_release_module = load_script('check_release')


@pytest.mark.parametrize(('suffix', 'header'), [
    ('.png', b'\x89PNG\r\n\x1a\n'), ('.jpg', b'\xff\xd8\xff'), ('.jpeg', b'\xff\xd8\xff'),
])
def test_release_scans_image_metadata_without_decoding_as_utf8(tmp_path, monkeypatch, capsys,
                                                             suffix, header):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    for directory in ('card', 'dist'):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / 'taggle-card.js').write_text('// fixture\n')
    image = tmp_path / f'image{suffix}'
    image.write_bytes(header + b'\xff\x00')
    monkeypatch.setattr(check_release_module, 'ROOT', tmp_path)
    assert check_release_module.check() == 0
    # Image text metadata must still be subject to the existing privacy guard.
    private_header = b'-----BEGIN ' + b'PRIVATE KEY-----'
    image.write_bytes(image.read_bytes() + private_header)
    assert check_release_module.check() == 1
    assert f'image{suffix}: privacy guard matched' in capsys.readouterr().out


@pytest.fixture
def release_tree(tmp_path):
    (tmp_path / 'addon').mkdir()
    for name in ('addon/config.yaml', 'pyproject.toml', 'addon/pyproject.toml', 'CHANGELOG.md'):
        (tmp_path / name).write_bytes((ROOT / name).read_bytes())
    return tmp_path


def test_release_notes_stop_at_next_version(release_tree):
    (release_tree / 'CHANGELOG.md').write_text(
        '# Changelog\n\n## Unreleased\n\n- Future\n\n## 0.1.0\n\n- Released\n\n## 0.0.1\n\n- Older\n')
    assert prepare('v0.1.0', release_tree) == '- Released\n'


@pytest.mark.parametrize('name', ['addon/config.yaml', 'pyproject.toml', 'addon/pyproject.toml'])
def test_release_rejects_version_mismatch(release_tree, name):
    path = release_tree / name
    path.write_text(path.read_text().replace('0.1.0', '0.1.1'))
    with pytest.raises(ValueError, match='does not match'):
        prepare('v0.1.0', release_tree)


@pytest.mark.parametrize('tag', ['0.1.0', 'v0.1.0-rc1', 'v01.1.0', 'v0.1.0.1'])
def test_release_rejects_invalid_tags(release_tree, tag):
    with pytest.raises(ValueError, match='Release tag'):
        prepare(tag, release_tree)


@pytest.mark.parametrize('changelog', ['## 0.0.1\n- Older\n', '## 0.1.0\n\n## 0.0.1\n- Older\n'])
def test_release_requires_notes(release_tree, changelog):
    (release_tree / 'CHANGELOG.md').write_text(changelog)
    with pytest.raises(ValueError, match='No CHANGELOG'):
        prepare('v0.1.0', release_tree)


def test_owner_replacement_covers_tracked_and_untracked_files(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    placeholder = set_owner_module.PLACEHOLDER
    (tmp_path / 'config.yaml').write_text(f'image: ghcr.io/{placeholder}/addon-{{arch}}\n')
    subprocess.run(['git', 'add', 'config.yaml'], cwd=tmp_path, check=True)
    (tmp_path / 'README.md').write_text(f'Use {placeholder}')
    (tmp_path / '.gitignore').write_text('private.txt\n')
    (tmp_path / 'private.txt').write_text(placeholder)
    (tmp_path / 'binary').write_bytes(b'\xff\x00')
    changed = set_owner_module.set_owner('Example-Org', tmp_path)
    assert set(changed) == {Path('config.yaml'), Path('README.md')}
    assert (tmp_path / 'config.yaml').read_text() == 'image: ghcr.io/example-org/addon-{arch}\n'
    assert (tmp_path / 'README.md').read_text() == 'Use example-org'
    assert (tmp_path / 'private.txt').read_text() == placeholder
    assert set_owner_module.set_owner('Example-Org', tmp_path) == []


@pytest.mark.parametrize('owner', ['', '../bad', 'https://github.com/example', '-bad', 'bad-', 'a' * 40])
def test_owner_rejects_invalid_names(tmp_path, owner):
    with pytest.raises(ValueError, match='Owner must be'):
        set_owner_module.set_owner(owner, tmp_path)
