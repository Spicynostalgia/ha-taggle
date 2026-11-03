"""Neighbourhood privacy and aggregates, using synthetic protocol frames only."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from taggle_rx.config import Config
from taggle_rx.mqtt import NEIGHBOURHOOD_ENTITIES, Publisher
from taggle_rx.store import Store

from .test_store import config, frame

DAY = datetime(2026, 1, 1, tzinfo=timezone.utc)
NEIGHBOURS = (234567, 345678, 456789)


def observe(store, identifier, *, intervals=6, delta=10, day=DAY):
    # The first frame recovers two slots, then each new frame adds one.
    for hour in range(2, intervals + 1):
        store.frame(frame(identifier=identifier, sequence=hour,
                          counts=(100 + hour * delta, 100 + (hour - 1) * delta,
                                  100 + (hour - 2) * delta)), day + timedelta(hours=hour))


def test_salt_hmac_and_serialized_privacy(tmp_path, caplog, monkeypatch):
    # Fixed random draws keep literal-byte privacy checks free of chance substring matches.
    random_bytes = Mock(side_effect=[bytes(range(32)), bytes(range(32, 64))])
    monkeypatch.setattr('taggle_rx.store.os.urandom', random_bytes)
    cfg = config(tmp_path, jsonl_logging=True)
    client = Mock()
    publisher = Publisher(cfg, client)
    store = Store(cfg, publisher)
    for identifier in NEIGHBOURS:
        observe(store, identifier)
    store.frame(frame(), DAY + timedelta(hours=7))
    store.refresh(DAY + timedelta(hours=8))
    publisher.announce()
    salt = (tmp_path / 'neighbourhood.salt').read_bytes()
    assert len(salt) == 32
    assert (tmp_path / 'neighbourhood.salt').stat().st_mode & 0o777 == 0o600
    assert len(store.neighbours) == 3
    for identifier in NEIGHBOURS:
        expected = hmac.new(salt, str(identifier).encode(), hashlib.sha256).hexdigest()[:16]
        assert expected in store.neighbours
    # Inspect actual serialized disk, MQTT topic/payload and captured log bytes.
    surfaces = [p.read_bytes() for p in tmp_path.iterdir() if p.suffix in ('.json', '.jsonl')]
    surfaces += [(str(c.args[0]) + '\n' + c.args[1]).encode()
                 for c in client.publish.call_args_list]
    surfaces.append(caplog.text.encode())
    for surface in surfaces:
        for identifier in NEIGHBOURS:
            for literal in (str(identifier), format(identifier, 'x'), format(identifier, 'X')):
                assert literal.encode() not in surface
        assert salt.hex().encode() not in surface
        for key in store.neighbours:
            if b'"neighbours"' not in surface:
                assert key.encode() not in surface
    # A restart preserves salt and identities; a different install cannot correlate keys.
    restored = Store(cfg)
    assert restored.salt == salt
    assert restored.neighbour_key(NEIGHBOURS[0]) == store.neighbour_key(NEIGHBOURS[0])
    other = Store(config(tmp_path / 'other'))
    assert other.neighbour_key(NEIGHBOURS[0]) != store.neighbour_key(NEIGHBOURS[0])
    assert [call.args for call in random_bytes.call_args_list] == [(32,), (32,)]


def test_floor_and_independent_aggregate_cohorts(tmp_path):
    store = Store(config(tmp_path, neighbourhood_min_meters=1))
    assert store.config.neighbourhood_min_meters == 3
    for identifier in NEIGHBOURS[:2]:
        observe(store, identifier)
    assert all(value is None for value in store.neighbourhood_snapshot(DAY + timedelta(hours=8)).values())
    # Encrypted heard count reaches the floor; usage still has just two contributors.
    store.frame(frame(identifier=NEIGHBOURS[2], size=24), DAY + timedelta(hours=7))
    result = store.neighbourhood_snapshot(DAY + timedelta(hours=8))
    assert result['meters_heard'] == 3
    assert all(result[key] is None for key in result if key != 'meters_heard')
    observe(store, NEIGHBOURS[2])  # Earlier frames cannot override the encrypted observation.
    assert store.neighbourhood_snapshot(DAY + timedelta(hours=8))['average_today'] is None


def test_qualification_average_median_and_partial_coverage(tmp_path):
    store = Store(config(tmp_path))
    for identifier, delta in zip(NEIGHBOURS, (10, 20, 90), strict=True):
        observe(store, identifier, delta=delta)
    result = store.neighbourhood_snapshot(DAY + timedelta(hours=8))
    assert result == dict(meters_heard=3, meters_counted=3, average_today=240,
                          median_today=120, average_last_hour=40)
    # Six intervals at exactly 75% of eight elapsed clock hours qualifies, without scaling.
    result = store.neighbourhood_snapshot(DAY + timedelta(hours=8, minutes=1))
    assert result['average_today'] is None
    assert result['average_last_hour'] is None
    for identifier in NEIGHBOURS:
        store.neighbours[store.neighbour_key(identifier)]['hours'].pop(next(iter(
            store.neighbours[store.neighbour_key(identifier)]['hours'])))
    # Five intervals never qualify, even early enough for 75% coverage.
    assert store.neighbourhood_snapshot(DAY + timedelta(hours=6))['meters_counted'] is None


def test_configured_exclusion_and_encrypted_exclusion(tmp_path):
    store = Store(config(tmp_path))
    observe(store, 123456)
    assert not store.neighbours
    for identifier in NEIGHBOURS:
        observe(store, identifier)
    store.frame(frame(identifier=NEIGHBOURS[0], size=24), DAY + timedelta(hours=7))
    result = store.neighbourhood_snapshot(DAY + timedelta(hours=8))
    assert result['meters_heard'] == 3
    assert result['meters_counted'] is None
    assert result['average_last_hour'] is None


def test_disabled_wipes_state_and_salt_on_startup(tmp_path):
    cfg = config(tmp_path)
    store = Store(cfg)
    store.frame(frame(identifier=NEIGHBOURS[0]), datetime.now(timezone.utc))
    assert json.loads((tmp_path / 'state.json').read_bytes())['neighbours']
    disabled = Store(config(tmp_path, neighbourhood=False))
    assert not disabled.neighbours
    assert disabled.salt is None
    assert not (tmp_path / 'neighbourhood.salt').exists()
    assert 'neighbours' not in json.loads((tmp_path / 'state.json').read_bytes())
    before = (tmp_path / 'state.json').read_bytes()
    disabled.frame(frame(identifier=NEIGHBOURS[1]), DAY)
    disabled.refresh(DAY)
    assert (tmp_path / 'state.json').read_bytes() == before


def test_pruning_and_newly_configured_meter_removed_on_startup(tmp_path):
    now = datetime.now(timezone.utc)
    store = Store(config(tmp_path))
    for identifier, age in zip(NEIGHBOURS, (8, 7, 0), strict=True):
        store.frame(frame(identifier=identifier), now - timedelta(days=age))
    store.refresh(now)
    assert len(store.neighbours) == 2
    assert store.neighbour_key(NEIGHBOURS[0]) not in store.neighbours
    # Reclassification must not leave a configured meter in the anonymous cohort.
    cfg = Config.from_dict({'meter_ids': [123456, NEIGHBOURS[2]], 'data_dir': str(tmp_path)})
    restored = Store(cfg)
    assert restored.neighbour_key(NEIGHBOURS[2]) not in restored.neighbours
    assert restored.neighbour_key(NEIGHBOURS[2]) not in (tmp_path / 'state.json').read_text()


def test_wrap_dedupe_gaps_and_restart_reuse(tmp_path):
    now = datetime.now(timezone.utc)
    store = Store(config(tmp_path))
    identifier = NEIGHBOURS[0]
    first = frame(identifier=identifier, sequence=255, counts=(2, 65530, 65520))
    store.frame(first, now)
    store.frame(first, now + timedelta(seconds=5))
    restored = Store(config(tmp_path))
    restored.frame(frame(identifier=identifier, sequence=0, counts=(11, 2, 65530)), now + timedelta(hours=1))
    meter = restored.neighbours[restored.neighbour_key(identifier)]
    assert meter['meter_count'] == 27
    assert len(meter['hours']) == 3
    restored.frame(frame(identifier=identifier, sequence=5, counts=(50, 40, 30)), now + timedelta(hours=6))
    assert meter['meter_count'] == 47
    assert len(meter['hours']) == 5


def test_local_interval_end_date_and_midnight_refresh(tmp_path):
    publisher = Mock()
    store = Store(config(tmp_path, timezone='Etc/GMT-2'), publisher)
    for identifier in NEIGHBOURS:
        observe(store, identifier, day=DAY - timedelta(hours=2))
    store.refresh(DAY + timedelta(hours=6))  # 08:00 local, six of eight hours observed.
    assert publisher.publish_neighbourhood.call_args.args[0]['average_today'] == 60
    store.refresh(DAY + timedelta(hours=22))  # Local midnight resets today's cohort.
    result = publisher.publish_neighbourhood.call_args.args[0]
    assert result['average_today'] is None
    assert result['meters_counted'] is None


@pytest.mark.parametrize(('scales', 'override', 'expected'), [
    ({}, None, 60), ({'123456': 2.5}, None, 150), ({'123456': 2.5}, 3, 180),
])
def test_calibration_fallback_override_comparison_and_refresh(tmp_path, scales, override, expected):
    cfg = config(tmp_path, litres_per_count=scales, neighbourhood_litres_per_count=override)
    publisher = Mock()
    store = Store(cfg, publisher)
    for identifier in NEIGHBOURS:
        observe(store, identifier)
    observe(store, 123456, delta=20)
    store.refresh(DAY + timedelta(hours=8))
    assert publisher.publish_neighbourhood.call_args.args[0]['average_today'] == expected
    value = publisher.publish.call_args.args[1]['vs_neighbourhood_today']
    assert value == pytest.approx(120 * scales.get('123456', 1) / expected * 100)
    store.refresh(DAY + timedelta(hours=9))
    assert publisher.publish.call_args.args[1]['vs_neighbourhood_today'] is None


@pytest.mark.parametrize('neighbourhood', [False, True])
@pytest.mark.parametrize('qualified', [False, True])
@pytest.mark.parametrize('event', ['frame', 'refresh', 'window_expiry', 'reading'])
def test_every_meter_publish_preserves_comparison(tmp_path, neighbourhood, qualified, event):
    publisher = Mock()
    store = Store(config(tmp_path, neighbourhood=neighbourhood), publisher)
    if qualified:
        for identifier in NEIGHBOURS:
            observe(store, identifier)
    observe(store, 123456, delta=20)
    publisher.publish.reset_mock()
    now = DAY + timedelta(hours=6, minutes=10)
    if event == 'frame':
        store.frame(frame(sequence=6, counts=(220, 200, 180)), now)
    elif event == 'refresh':
        store.refresh(now)
    elif event == 'window_expiry':
        store.expire_read_windows(now)
    else:
        store.command(123456, 'reading', '1597.765', now)
    publisher.publish.assert_called_once()
    identifier, state = publisher.publish.call_args.args
    assert identifier == 123456
    if neighbourhood:
        assert 'vs_neighbourhood_today' in state
        if qualified:
            assert state['vs_neighbourhood_today'] == pytest.approx(200)
        else:
            assert state['vs_neighbourhood_today'] is None
    else:
        assert 'vs_neighbourhood_today' not in state
    if event == 'window_expiry':
        assert state['read_dial_now']['state'] == 'OFF'


def test_first_configured_calibration_and_incompatible_units(tmp_path):
    cfg = config(tmp_path, meter_ids=[345678, 123456], litres_per_count={'123456': 2})
    assert cfg.neighbourhood_factor is None
    cfg.neighbourhood_litres_per_count = 3
    store = Store(cfg)
    assert store.comparison(345678, {'today': 10}, {'average_today': 20}) is None
    assert store.comparison(123456, {'today': 10, 'today_litres': 20}, {'average_today': 0}) is None


def test_discovery_nulls_reconnect_birth_and_disabled_removal(tmp_path):
    cfg = config(tmp_path)
    client = Mock()
    publisher = Publisher(cfg, client)
    publisher.announce()
    for key in NEIGHBOURHOOD_ENTITIES:
        spec = publisher.neighbourhood_discovery(key)
        assert spec['device']['name'] == 'Taggle neighbourhood'
        assert spec['state_class'] == 'measurement'
        assert spec['default_entity_id'] == f'sensor.taggle_neighbourhood_{key}'
    state = dict(meters_heard=4, meters_counted=None, average_today=None,
                 median_today=None, average_last_hour=None)
    publisher.publish_neighbourhood({**state, 'forbidden': 'private'})
    for action in (lambda: publisher.on_connect(client, None, None, 0),
                   lambda: publisher.on_message(client, None, Mock(topic='homeassistant/status', payload=b'online'))):
        client.publish.reset_mock()
        action()
        messages = [json.loads(c.args[1]) for c in client.publish.call_args_list
                    if c.args[0] == 'taggle/neighbourhood/state']
        assert messages == [state]
        assert all(c.kwargs == {'qos': 1, 'retain': True} for c in client.publish.call_args_list)
    client.publish.reset_mock()
    Publisher(config(tmp_path, neighbourhood=False), client).announce()
    assert ('taggle/neighbourhood/state', '') in [c.args for c in client.publish.call_args_list]
    assert sum(c.args[1] == '' and '_neighbourhood/' in c.args[0]
               for c in client.publish.call_args_list) == 5


@pytest.mark.parametrize('values', [
    {'neighbourhood': 'false'}, {'neighbourhood_min_meters': True},
    {'neighbourhood_min_meters': 3.2}, {'neighbourhood_litres_per_count': 0},
    {'neighbourhood_litres_per_count': True}, {'neighbourhood_litres_per_count': float('nan')},
])
def test_invalid_config(tmp_path, values):
    with pytest.raises(ValueError):
        config(tmp_path, **values)


def test_custom_floor_and_heard_window(tmp_path):
    store = Store(config(tmp_path, neighbourhood_min_meters=4))
    for identifier in NEIGHBOURS:
        observe(store, identifier)
    assert all(v is None for v in store.neighbourhood_snapshot(DAY + timedelta(hours=8)).values())
    observe(store, 567890)
    assert store.neighbourhood_snapshot(DAY + timedelta(hours=8))['meters_counted'] == 4
    assert store.neighbourhood_snapshot(DAY + timedelta(hours=30))['meters_heard'] == 4
    assert store.neighbourhood_snapshot(DAY + timedelta(hours=30, seconds=1))['meters_heard'] is None


def test_lost_salt_and_removed_configured_ids_are_wiped_from_checkpoint(tmp_path):
    now = datetime.now(timezone.utc)
    store = Store(config(tmp_path))
    store.frame(frame(), now)
    store.frame(frame(identifier=NEIGHBOURS[0]), now)
    old_key = store.neighbour_key(NEIGHBOURS[0])
    (tmp_path / 'neighbourhood.salt').unlink()
    cfg = config(tmp_path, meter_ids=[NEIGHBOURS[1]])
    restored = Store(cfg)
    assert not restored.neighbours
    assert not restored.meters
    serialized = (tmp_path / 'state.json').read_bytes()
    assert old_key.encode() not in serialized
    assert b'123456' not in serialized


def test_bad_salt_exception_has_no_neighbour_id(tmp_path):
    store = Store(config(tmp_path))
    store.frame(frame(identifier=NEIGHBOURS[0]), datetime.now(timezone.utc))
    (tmp_path / 'neighbourhood.salt').write_bytes(b'invalid')
    with pytest.raises(ValueError, match='invalid neighbourhood salt length') as error:
        Store(config(tmp_path))
    for identifier in NEIGHBOURS:
        assert str(identifier) not in str(error.value)
        assert format(identifier, 'x') not in str(error.value)
