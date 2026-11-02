"""Synthetic hourly histories exercise both possible-leak rules and their hooks."""
import copy
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from taggle_rx.config import Config
from taggle_rx.leak import ATTRIBUTES, evaluate
from taggle_rx.mqtt import Publisher
from taggle_rx.store import Store

from .test_store import config, frame

UTC = timezone.utc
BASE = datetime(2026, 1, 1, 12, tzinfo=UTC)


def hours(start, counts):
    return {str(round(start.timestamp() / 3600) + i):
            {'end': (start + timedelta(hours=i)).isoformat(), 'counts': count}
            for i, count in enumerate(counts) if count is not None}


def run(history, now=None, previous=None, **options):
    cfg = Config.from_dict({'meter_ids': [123456], **options})
    if now is None:
        now = max(datetime.fromisoformat(h['end']) for h in history.values())
    return evaluate(history, now, cfg, ZoneInfo(cfg.timezone), previous)


def test_continuous_coverage_boundary_gaps_and_zero_recovery():
    # 20/24 qualifies, 19/24 does not.
    nineteen = hours(BASE, [1] * 19)
    assert not run(nineteen)['_continuous']
    history = hours(BASE, [1] * 20)
    original = copy.deepcopy(history)
    result = run(history)
    assert result['state'] == 'ON'
    assert result['reason'] == 'continuous flow for 24 h'
    assert result['hours_with_flow_last_24h'] == result['observed_hours'] == 20
    assert result['longest_zero_run_hours'] == 0
    assert history == original
    gaps = hours(BASE, [1, None, 1, 1, 1, 1] * 4)
    assert run(gaps)['_continuous']
    gaps = hours(BASE, [1, None, 1, 1, None, 1] * 4)
    assert not run(gaps)['_continuous']
    # Silence/under-coverage does not clear an established hint.
    later = BASE + timedelta(hours=50)
    latched = run(history, now=later, previous=result)
    assert latched['_continuous']
    assert latched['observed_hours'] == 0
    recovered = {**history, **hours(later, [0])}
    assert not run(recovered, previous=latched)['_continuous']
    # A zero in the qualifying window prevents activation.
    assert not run(hours(BASE, [1] * 19 + [0] + [1] * 4))['_continuous']


def test_continuous_custom_duration_and_reactivation_after_zero():
    history = hours(BASE, [1] * 4)
    result = run(history, leak_continuous_hours=4)
    assert result['reason'] == 'continuous flow for 4 h'
    history.update(hours(BASE + timedelta(hours=4), [0]))
    cleared = run(history, previous=result, leak_continuous_hours=4)
    assert cleared['state'] == 'OFF'
    history.update(hours(BASE + timedelta(hours=5), [2] * 4))
    assert run(history, previous=cleared, leak_continuous_hours=4)['_continuous']


def test_missing_hours_break_zero_runs_and_future_intervals_are_ignored():
    history = hours(BASE, [0, 0, None, 0, 0, 0, 2, 0])
    history.update(hours(BASE + timedelta(days=1), [1] * 24))
    result = run(history, now=BASE + timedelta(hours=7))
    assert result['longest_zero_run_hours'] == 3
    assert result['observed_hours'] == 7
    assert result['hours_with_flow_last_24h'] == 1
    assert result['last_evaluated'] == (BASE + timedelta(hours=7)).isoformat()
    assert result['state'] == 'OFF'


def test_continuous_uses_elapsed_hours_across_dst():
    # Sydney skips one local hour, but elapsed UTC coverage still has 24 slots.
    start = datetime(2026, 10, 3, 15, tzinfo=UTC)
    history = hours(start, [1] * 24)
    result = run(history, timezone='Australia/Sydney')
    assert result['_continuous']
    assert result['observed_hours'] == result['hours_with_flow_last_24h'] == 24


@pytest.mark.parametrize('zone, local_day, expected', [
    ('Australia/Brisbane', '2026-10-04', 4),  # No daylight saving.
    ('Australia/Sydney', '2026-10-04', 3),   # 02:00 does not exist.
    ('Australia/Sydney', '2026-04-05', 5),   # 02:00 occurs twice.
])
def test_night_local_window_across_dst(zone, local_day, expected):
    local_start = datetime.fromisoformat(local_day).replace(tzinfo=ZoneInfo(zone))
    start = local_start.astimezone(UTC)
    history = hours(start, [2] * 8)
    now = start + timedelta(hours=7)
    result = run(history, now=now, timezone=zone)
    assert result['state'] == 'ON'
    assert result['reason'] == 'night flow'
    assert result['night_pulses'] == expected * 2
    assert result['observed_hours'] == 8


def test_night_gaps_threshold_and_half_open_boundaries():
    zone = 'Australia/Brisbane'
    start = datetime(2026, 1, 1, 0, tzinfo=ZoneInfo(zone)).astimezone(UTC)
    # 01:00 inclusive, 05:00 exclusive; outside zeroes must not prevent a hint.
    history = hours(start, [0, 2, None, 2, 2, 0])
    result = run(history, timezone=zone, leak_night_min_pulses=2)
    assert result['reason'] == 'night flow'
    assert result['night_pulses'] == 6
    assert run(hours(start, [0, 2, None, None, 2, 0]), timezone=zone)['state'] == 'OFF'
    assert run(hours(start, [0, 2, 1, 2, 2, 0]), timezone=zone,
               leak_night_min_pulses=2)['state'] == 'OFF'


def test_night_crosses_midnight_and_latches_until_later_clean_window():
    options = dict(timezone='Australia/Brisbane', leak_night_start='23:00', leak_night_end='03:00')
    start = datetime(2026, 1, 1, 23, tzinfo=ZoneInfo(options['timezone'])).astimezone(UTC)
    history = hours(start, [1, 1, 1])
    result = run(history, **options)
    assert result['reason'] == 'night flow'
    # Daytime zeroes and a zero later in the triggering window do not clear it.
    history.update(hours(start + timedelta(hours=3), [0, 0, 0, 0]))
    result = run(history, previous=result, **options)
    assert result['state'] == 'ON'
    assert result['night_pulses'] == 3
    # Fewer than 3 observed intervals the next night cannot establish recovery.
    history.update(hours(start + timedelta(days=1), [0, None, 0]))
    result = run(history, now=start + timedelta(hours=28), previous=result, **options)
    assert result['state'] == 'ON'
    # A later night with >=3 observations and a below-threshold hour clears
    # only after that window ends, including when completion is a refresh.
    history.update(hours(start + timedelta(days=2), [0, 1, 1]))
    result = run(history, previous=result, **options)
    assert result['state'] == 'ON'
    result = run(history, now=start + timedelta(hours=52), previous=result, **options)
    assert result['state'] == 'OFF'
    assert result['reason'] is None
    assert result['night_pulses'] == 2


def test_both_reasons_and_independent_recovery():
    start = datetime(2026, 1, 1, 6, tzinfo=UTC)
    history = hours(start, [1] * 24)
    result = run(history)
    assert result['_continuous'] and result['_night']
    assert result['reason'] == 'continuous flow for 24 h'
    history.update(hours(start + timedelta(days=1), [0]))
    result = run(history, previous=result)
    assert result['reason'] == 'night flow'


def test_settings_change_recomputes_instead_of_preserving_old_rule_latches():
    history = hours(BASE, [1] * 4)
    result = run(history, leak_continuous_hours=4)
    assert result['_continuous']
    assert not run(history, previous=json.loads(json.dumps(result)), leak_continuous_hours=24)['_continuous']


@pytest.mark.parametrize('option,value', [
    ('leak_detection', 'true'), ('leak_detection', 1),
    ('leak_continuous_hours', True), ('leak_continuous_hours', 0),
    ('leak_continuous_hours', 169), ('leak_continuous_hours', 24.0),
    ('leak_night_min_pulses', False), ('leak_night_min_pulses', 0),
    ('leak_night_min_pulses', 65536), ('leak_night_min_pulses', 1.5),
    ('leak_night_start', '1:00'), ('leak_night_start', '24:00'),
    ('leak_night_end', '05:60'), ('leak_night_end', None),
    ('leak_night_end', '01:00'),
])
def test_invalid_options(option, value):
    with pytest.raises(ValueError):
        Config.from_dict({'meter_ids': [123456], option: value})


@pytest.mark.parametrize('prefix', ['taggle', 'house/taggle'])
def test_discovery_payload_wire_attributes_reconnect_and_disable(prefix):
    cfg = Config.from_dict({'meter_ids': [123456], 'mqtt': {'topic_prefix': prefix}})
    client = Mock()
    publisher = Publisher(cfg, client)
    publisher.announce()
    topic = f'homeassistant/binary_sensor/{prefix.replace("/", "_")}_123456/possible_leak/config'
    payload = next(json.loads(c.args[1]) for c in client.publish.call_args_list if c.args[0] == topic)
    assert payload['name'] == 'Possible leak'
    assert payload['device_class'] == 'problem'
    assert payload['default_entity_id'] == 'binary_sensor.taggle_123456_possible_leak'
    assert payload['unique_id'] == f'{prefix}_123456_possible_leak'
    assert 'object_id' not in payload
    assert payload['availability'] == [
        {'topic': f'{prefix}/status'}, {'topic': f'{prefix}/123456/counts_available'}]
    assert payload['availability_mode'] == 'all'
    assert payload['value_template'] == '{{ value_json.state }}'
    assert (payload['payload_on'], payload['payload_off']) == ('ON', 'OFF')
    assert payload['device']['identifiers'] == [f'{prefix}_123456']
    assert payload['json_attributes_topic'] == payload['state_topic'] == f'{prefix}/123456/leak'
    assert all(f'{key}=value_json.{key}' in payload['json_attributes_template'] for key in ATTRIBUTES)
    assert not any('neighbourhood/possible_leak' in c.args[0] for c in client.publish.call_args_list)
    leak = run(hours(BASE, [1] * 24))
    publisher.publish(123456, {'last_seen': datetime.now(UTC).isoformat(), 'meter_count': 24,
                               'possible_leak': leak})
    for action in (publisher.announce, lambda: publisher.publish(123456, publisher.latest[123456])):
        client.publish.reset_mock()
        action()
        wire = next(json.loads(c.args[1]) for c in client.publish.call_args_list
                    if c.args[0] == payload['state_topic'])
        assert set(wire) == {'state', *ATTRIBUTES}
        assert wire['state'] == 'ON'
        assert wire['reason'] == 'continuous flow for 24 h'
        main_state = next(json.loads(c.args[1]) for c in client.publish.call_args_list
                          if c.args[0] == f'{prefix}/123456/state')
        assert 'possible_leak' not in main_state
        assert all(c.kwargs == {'qos': 1, 'retain': True} for c in client.publish.call_args_list)
    cfg.leak_detection = False
    client.publish.reset_mock()
    publisher.announce()
    assert any(c.args[:2] == (topic, '') for c in client.publish.call_args_list)
    assert any(c.args[:2] == (f'{prefix}/123456/leak', '') for c in client.publish.call_args_list)


def test_store_configured_only_restart_recovery_disabled_and_encrypted(tmp_path):
    cfg = config(tmp_path, leak_continuous_hours=2, log_all_meters=True)
    publisher = Mock()
    store = Store(cfg, publisher)
    store.frame(frame(), BASE)
    result = store.snapshot(123456, BASE)['possible_leak']
    assert result['reason'] == 'continuous flow for 2 h'
    assert store.meters['123456']['leak'] == result
    restored = Store(cfg, publisher)
    assert restored.snapshot(123456, BASE)['possible_leak'] == result
    restored.frame(frame(identifier=234567), BASE)
    assert not any('leak' in neighbour for neighbour in restored.neighbours.values())
    assert set(restored.meters) == {'123456'}
    assert all(call.args[0] == 123456 for call in publisher.publish.call_args_list)
    restored.frame(frame(sequence=8, counts=(120, 120, 110)), BASE + timedelta(hours=1))
    assert restored.snapshot(123456, BASE + timedelta(hours=1))['possible_leak']['state'] == 'OFF'
    restored.frame(frame(size=24), BASE + timedelta(hours=2))
    assert 'possible_leak' not in restored.snapshot(123456, BASE + timedelta(hours=2))
    cfg.leak_detection = False
    assert 'possible_leak' not in Store(cfg).snapshot(123456, BASE + timedelta(hours=2))


def test_night_recovery_waits_for_later_ambiguous_dst_end():
    zone = ZoneInfo('Australia/Sydney')
    options = dict(timezone=zone.key, leak_night_start='00:00', leak_night_end='02:30')
    start = datetime(2026, 4, 4, 0, 15, tzinfo=zone).astimezone(UTC)
    history = hours(start, [1, 1, 1])
    result = run(history, **options)
    assert result['_night']
    next_start = datetime(2026, 4, 5, 0, 15, tzinfo=zone).astimezone(UTC)
    history.update(hours(next_start, [0, 0, 0]))
    first_end = datetime(2026, 4, 5, 2, 45, tzinfo=zone, fold=0).astimezone(UTC)
    result = run(history, now=first_end, previous=result, **options)
    assert result['_night']
    second_end = datetime(2026, 4, 5, 2, 45, tzinfo=zone, fold=1).astimezone(UTC)
    assert not run(history, now=second_end, previous=result, **options)['_night']


def test_empty_history_and_disabled_clear_meter(tmp_path):
    assert run({}, now=BASE)['state'] == 'OFF'
    store = Store(config(tmp_path, leak_detection=False, leak_continuous_hours=2))
    store.frame(frame(), BASE)
    assert 'possible_leak' not in store.snapshot(123456, BASE)
    assert 'leak' not in store.meters['123456']


def test_continuous_recovered_zero_is_not_hidden_by_reception_gap():
    history = hours(BASE, [1] * 20)
    result = run(history)
    assert result['_continuous']
    # After a two-hour gap, the frame recovers the last two intervals, including
    # a zero that was not available at the last refresh.
    result = run(history, now=BASE + timedelta(hours=21, minutes=30), previous=result)
    history.update(hours(BASE + timedelta(hours=21), [0, 1]))
    result = run(history, previous=result)
    assert not result['_continuous']


def test_next_night_with_late_zero_clears_without_retriggering_on_refresh():
    start = datetime(2026, 1, 1, 1, tzinfo=UTC)
    history = hours(start, [1, 1, 1, 1])
    result = run(history)
    assert result['reason'] == 'night flow'
    # An existing night hint must not postpone recovery merely because the
    # following night began with three positive observations before a zero.
    history.update(hours(start + timedelta(days=1), [1, 1, 1, 0]))
    result = run(history, previous=result)
    assert result['reason'] == 'night flow'
    complete = start + timedelta(hours=28)
    result = run(history, now=complete, previous=result)
    assert result['state'] == 'OFF'
    assert run(history, now=complete + timedelta(minutes=1), previous=result)['state'] == 'OFF'
