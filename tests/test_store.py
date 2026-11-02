import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from taggle_rx.config import Config
from taggle_rx.protocol import decode_frame
from taggle_rx.store import Store

from .synthetic import air, frame_bytes

START = datetime(2026, 1, 1, 12, 15, tzinfo=timezone.utc)


def frame(**kwargs):
    result = decode_frame(air(frame_bytes(**kwargs)))
    return {**result, 'snr_median_db': 20.0, 'signal_level_dbfs': -35.0}


def config(tmp_path, **kwargs):
    return Config.from_dict({'meter_ids': [123456], 'data_dir': str(tmp_path), **kwargs})


def test_filter_before_logging_persistence_or_publishing(tmp_path):
    publisher = Mock()
    store = Store(config(tmp_path, jsonl_logging=True, neighbourhood=False), publisher)
    store.frame(frame(identifier=234567), START)
    assert not list(tmp_path.iterdir())
    publisher.publish.assert_not_called()
    assert not store.meters


def test_explicit_log_all_does_not_discover_other_meters(tmp_path):
    publisher = Mock()
    store = Store(config(tmp_path, log_all_meters=True, jsonl_logging=True), publisher)
    store.frame(frame(identifier=234567, size=24), START)
    assert not store.meters
    publisher.publish.assert_not_called()
    row = json.loads(next(tmp_path.glob('*.jsonl')).read_text())
    assert row['meter_id'] == 234567
    assert 'counts' not in row
    assert not any('hex' in k or 'body' in k for k in row)


def test_scan_prints_counts_only_for_configured_meters_and_never_writes(tmp_path):
    results = []
    path = tmp_path / 'absent'
    store = Store(config(path), scan=results.append)
    store.frame(frame(identifier=234567), START)
    store.frame(frame(), START)
    assert 'counts' not in results[0]
    assert results[1]['counts'] == [120, 110, 104]
    assert not path.exists()


@pytest.mark.parametrize('configured', [False, True])
@pytest.mark.parametrize('size', [18, 21, 24])
def test_scan_frame_time_and_precision(tmp_path, configured, size, caplog, monkeypatch):
    now = 1000.
    monkeypatch.setattr('taggle_rx.store.time.monotonic', lambda: now)
    results = []
    path = tmp_path / 'absent'
    store = Store(config(path), scan=results.append)
    decoded = {**frame(identifier=123456 if configured else 234567, size=size),
               'snr_median_db': 30.087156629613467, 'signal_level_dbfs': -40.90190578364269}
    original = dict(decoded)
    with caplog.at_level('INFO'):
        store.frame(decoded, START.astimezone(timezone(timedelta(hours=10))))
        now += 900
        store.heartbeat()
    expected = {'time': '2026-01-01T12:15:00+00:00', 'meter_id': decoded['meter_id'],
                'snr_median_db': 30.1, 'signal_level_dbfs': -40.9}
    if configured and size != 24:
        expected['counts'] = decoded['counts']
    assert results == [expected]
    assert decoded == original
    assert not path.exists()
    assert not caplog.records


@pytest.mark.parametrize('neighbourhood', [False, True])
def test_frame_logs_and_heartbeat_only_expose_configured_ids(tmp_path, caplog, monkeypatch, neighbourhood):
    now = 1000.
    monkeypatch.setattr('taggle_rx.store.time.monotonic', lambda: now)
    # Even log-all mode must never put neighbour IDs in normal logs.
    store = Store(config(tmp_path, neighbourhood=neighbourhood, log_all_meters=True))
    with caplog.at_level('INFO'):
        store.frame(frame(counts=(2, 65530, 65520)), START)
        store.frame(frame(size=24), START + timedelta(seconds=1))
        store.frame(frame(identifier=234567), START)
        store.frame(frame(identifier=234567), START)
        store.frame(frame(identifier=345678, size=24), START)
        now += 899
        store.heartbeat()
        assert len(caplog.records) == 2
        now += 1
        store.heartbeat()
        store.heartbeat()
        now += 900
        store.heartbeat()
        store.frame(frame(identifier=345678), START)
        now += 900
        store.heartbeat()
    assert caplog.messages == [
        'Meter 123456: +8 pulses last hour, SNR 20.0 dB',
        'Meter 123456: counts unavailable, SNR 20.0 dB',
        'still listening: 3 frames from 2 other meters heard in the last 15 min',
        'still listening: 0 frames from 0 other meters heard in the last 15 min',
        'still listening: 1 frames from 1 other meters heard in the last 15 min',
    ]
    assert all(record.levelname == 'INFO' for record in caplog.records)
    for identifier in (234567, 345678):
        assert str(identifier) not in caplog.text
    assert not store.other_meters
    assert store.other_frames == 0


def test_duplicate_history_restart_and_wrap(tmp_path):
    cfg = config(tmp_path, litres_per_count={'123456': 2.5})
    store = Store(cfg)
    first = frame(sequence=255, counts=(2, 65530, 65520))
    store.frame(first, START)
    state = store.snapshot(123456, START)
    assert state['last_hour'] == 8
    assert state['meter_count'] == 18
    assert state['total_litres'] == 45
    store.frame(first, START + timedelta(seconds=5))
    assert store.snapshot(123456, START)['meter_count'] == 18
    restored = Store(cfg)
    restored.frame(frame(sequence=0, counts=(11, 2, 65530)), START + timedelta(hours=1))
    state = restored.snapshot(123456, START + timedelta(hours=1))
    assert state['meter_count'] == 27
    assert state['total_litres'] == 67.5
    assert len(state['history']) == 3


def test_gaps_recover_only_two_known_intervals(tmp_path):
    store = Store(config(tmp_path))
    store.frame(frame(), START)
    store.frame(frame(sequence=12, counts=(300, 280, 260)), START + timedelta(hours=5))
    state = store.snapshot(123456, START + timedelta(hours=5))
    assert state['meter_count'] == 56
    assert len(state['history']) == 4
    assert 'total_litres' not in state


def test_scale_change_does_not_revalue_energy_baseline(tmp_path):
    store = Store(config(tmp_path))
    store.frame(frame(), START)
    scaled = Store(config(tmp_path, litres_per_count={'123456': 3}))
    scaled.frame(frame(sequence=8, counts=(130, 120, 110)), START + timedelta(hours=1))
    assert scaled.snapshot(123456, START)['total_litres'] == 30
    changed = Store(config(tmp_path, litres_per_count={'123456': 5}))
    changed.frame(frame(sequence=9, counts=(140, 130, 120)), START + timedelta(hours=2))
    assert changed.snapshot(123456, START)['total_litres'] == 80


def test_midnight_local_zone_and_refresh(tmp_path):
    publisher = Mock()
    store = Store(config(tmp_path, timezone='Etc/GMT-2'), publisher)
    before = datetime(2026, 1, 1, 21, 55, tzinfo=timezone.utc)
    store.frame(frame(), before)
    assert store.snapshot(123456, before)['today'] == 16
    after = before + timedelta(minutes=10)
    store.refresh(after)
    state = publisher.publish.call_args.args[1]
    assert state['today'] == 0
    assert state['last_seen'] == before.isoformat()


def test_encrypted_frames_do_not_republish_old_counts(tmp_path):
    store = Store(config(tmp_path))
    store.frame(frame(), START)
    store.frame(frame(size=24), START + timedelta(hours=1))
    result = store.snapshot(123456, START + timedelta(hours=1))
    assert result['encrypted'] is True
    assert 'meter_count' not in result
    assert 'last_hour' not in result


def test_old_frames_cannot_change_totals(tmp_path):
    store = Store(config(tmp_path))
    store.frame(frame(), START)
    store.frame(frame(sequence=1), START - timedelta(hours=6))
    assert store.snapshot(123456, START)['meter_count'] == 16


def test_sequence_full_wrap_and_bounded_history(tmp_path):
    store = Store(config(tmp_path))
    store.frame(frame(), START)
    store.frame(frame(sequence=8), START + timedelta(hours=257))
    assert store.snapshot(123456, START + timedelta(hours=257))['meter_count'] == 32
    assert len(store.meters['123456']['hours']) == 2


def test_corrupt_state_is_not_silently_reset(tmp_path):
    (tmp_path / 'state.json').write_text('{broken')
    with pytest.raises(ValueError):
        Store(config(tmp_path))


@pytest.mark.parametrize('existing_log', [False, True])
def test_private_data_directory_and_jsonl_permissions(tmp_path, existing_log):
    import os
    import stat

    data = tmp_path / 'receiver'
    previous_umask = os.umask(0)
    try:
        store = Store(config(data, jsonl_logging=True))
        log = data / f'{START.date()}.jsonl'
        if existing_log:
            log.write_text('{}\n')
            log.chmod(0o644)
        store.frame(frame(), START)
        store.frame(frame(sequence=8), START + timedelta(hours=1))
    finally:
        os.umask(previous_umask)
    assert stat.S_IMODE(data.stat().st_mode) == 0o700
    for path in (log, data / 'state.json', data / 'neighbourhood.salt'):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(rows) == 2 + existing_log
    assert rows[-1]['sequence'] == 8
