import json
import tomllib
from pathlib import Path

import yaml
from taggle_rx.config import Config

ROOT = Path(__file__).resolve().parents[1]


def test_example_and_addon_options_validate():
    Config.from_dict(json.loads((ROOT / 'config.example.json').read_text()))
    addon = yaml.safe_load((ROOT / 'addon/config.yaml').read_text())
    options = addon['options'].copy()
    options.pop('scan_minutes')
    options['meter_ids'] = [123456]
    Config.from_dict(options)
    assert addon['services'] == ['mqtt:need']
    assert addon['usb'] is True
    assert set(addon['arch']) == {'amd64', 'aarch64'}


def test_root_and_self_contained_addon_package_agree():
    root = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    addon = tomllib.loads((ROOT / 'addon/pyproject.toml').read_text())
    assert root['project'] == addon['project']
    assert root['tool']['setuptools']['packages'] == ['taggle_rx']
    assert addon['tool']['setuptools']['packages'] == ['taggle_rx']
    assert (ROOT / 'addon/requirements.txt').exists()


def test_ci_builds_both_architectures_without_push():
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    matrix = workflow['jobs']['containers']['strategy']['matrix']
    assert set(matrix['arch']) == {'amd64', 'aarch64'}
    assert set(matrix['image']) == {'addon', 'standalone'}
    build = workflow['jobs']['containers']['steps'][-1]
    assert build['with']['push'] is False
