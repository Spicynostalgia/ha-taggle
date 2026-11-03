

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from .synthetic import burst


@pytest.fixture(scope='module')
def scan_iq(tmp_path_factory):
    source = tmp_path_factory.mktemp('scan') / 'synthetic.cu8'
    source.write_bytes(burst())
    return source


@pytest.mark.parametrize('zone', ['UTC0', 'AEST-10'])
def test_scan_stdout_stays_json_with_utc_frame_time(tmp_path, scan_iq, zone):
    config = tmp_path / 'options.json'
    data = tmp_path / 'unused-data'
    config.write_text(json.dumps({'meter_ids': [123456], 'data_dir': str(data)}))
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = subprocess.run(
        [sys.executable, '-m', 'taggle_rx', '--config', str(config), '--scan', '1',
         '--input', str(scan_iq), '--start-utc', start.isoformat()],
        env={**os.environ, 'TZ': zone, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'addon')},
        capture_output=True, text=True, check=True)
    row, = [json.loads(line) for line in result.stdout.splitlines()]
    stamp = datetime.fromisoformat(row['time'])
    assert stamp.utcoffset() == timedelta(0)
    assert start <= stamp < start + timedelta(seconds=1)
    assert row['meter_id'] == 123456
    assert row['counts'] == [120, 110, 104]
    assert result.stderr == ''
    assert not data.exists()


@pytest.mark.parametrize(('zone', 'offset'), [('UTC0', 0), ('AEST-10', 10)])
def test_normal_logs_have_iso_local_timestamps(tmp_path, zone, offset):
    config = tmp_path / 'options.json'
    config.write_text(json.dumps({'meter_ids': [123456], 'neighbourhood': False,
                                  'data_dir': str(tmp_path / 'data')}))
    source = tmp_path / 'empty.cu8'
    source.write_bytes(b'')
    # A fresh process exercises basicConfig without pytest's logging handlers.
    # Mock the broker and decoder so no network or radio hardware is involved.
    script = ('import sys; from unittest.mock import Mock; import taggle_rx.cli as cli; '
              'cli.Publisher = Mock(); cli.Receiver = Mock(); sys.exit(cli.main(sys.argv[1:]))')
    before = datetime.now(timezone.utc).replace(microsecond=0)
    result = subprocess.run(
        [sys.executable, '-c', script, '--config', str(config), '--input', str(source),
         '--start-utc', '2026-01-01T00:00:00Z'],
        env={**os.environ, 'TZ': zone, 'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'addon')},
        capture_output=True, text=True, check=True)
    assert result.stdout == ''
    line, = result.stderr.splitlines()
    stamp, level, message = line.split(' ', 2)
    stamp = datetime.fromisoformat(stamp)
    assert 'T' in line.split(' ', 1)[0]
    assert stamp.utcoffset() == timedelta(hours=offset)
    assert before <= stamp <= datetime.now(timezone.utc)
    assert level == 'INFO'
    assert message.startswith('Listening on 922.2 MHz')


def test_retry_delay_backs_off_without_sdr_and_resets_after_data():
    from taggle_rx.cli import retry_delay
    delays, delay = [], 1
    for _ in range(8):
        delay = retry_delay(delay, False)
        delays.append(delay)
    assert delays == [2, 4, 8, 16, 32, 60, 60, 60]
    assert retry_delay(60, True) == 2
