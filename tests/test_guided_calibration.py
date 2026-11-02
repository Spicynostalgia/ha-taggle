"""Dial-to-radio integration, including the fictionalised 2 November hardware fixture."""
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from taggle_rx import calibration
from taggle_rx.store import Store

from .test_store import config, frame

ID = 123456
START = datetime(2026, 11, 2, 2, 41, tzinfo=timezone(timedelta(hours=10)))


def add(store, litres, stamp, **extra):
    store.command(ID, 'reading', json.dumps({'litres': litres, 'time': stamp.isoformat(), **extra}), stamp)
    return store.meters[str(ID)]['calibration']


def radio(store, hours, counts, sequence=None):
    store.frame(frame(counts=counts, sequence=(hours + 7) % 256 if sequence is None else sequence),
                START + timedelta(hours=hours))


def test_real_2_nov_fixture_pending_bounds_offset_and_restart(tmp_path):
    store = Store(config(tmp_path, timezone='Australia/Brisbane'))
    radio(store, 0, (46218, 46218, 46218))
    first = START + timedelta(minutes=2)
    cal = add(store, 1597361, first)
    assert 'Waiting for next transmission' in cal['status']
    radio(store, 1, (46218, 46218, 46218))
    assert cal['readings'][0]['count_interval'] == [46218, 46218]
    radio(store, 15, (46283, 46280, 46275))
    second = START + timedelta(hours=15, minutes=19)
    cal = add(store, 1597765, second, source='photo')
    assert cal['solution'] is None
    radio(store, 16, (46318, 46283, 46280))
    assert cal['bounds'] == pytest.approx([4.04, 404 / 65])
    solution = cal['solution']
    assert solution['factor'] == 5
    assert solution['method'] == 'standard value'
    assert solution['offset'] == 1597361 - 46218 * 5
    assert cal['readings'][1]['count_interval'] == [46283, 46318]
    assert all(r['used'] for r in cal['readings'])
    state = store.snapshot(ID, second + timedelta(hours=1))
    assert state['meter_reading'] == 1597861
    assert state['calibration']['next_transmission_expected'] == 'Next transmission expected ≈ 19:41'
    assert 'within a few minutes' in state['calibration']['guidance']
    restored = Store(config(tmp_path, timezone='Australia/Brisbane'))
    assert restored.meters[str(ID)]['calibration']['solution'] == json.loads(json.dumps(solution))
    assert restored.snapshot(ID, second)['meter_reading'] == state['meter_reading']
    # Synthetic follow-up checks validation; the real 3 November utility reading is not supplied.
    radio(restored, 40, (46418, 46418, 46418))
    cal = add(restored, 1598361, START + timedelta(hours=40))
    assert cal['readings'][-1]['used']
    assert cal['readings'][-1]['residual_litres'] == pytest.approx(0)


def test_manual_only_two_mid_hour_readings_and_photo_time(tmp_path):
    store = Store(config(tmp_path, timezone='Australia/Brisbane'))
    radio(store, 0, (100, 95, 90))
    store.command(ID, 'reading_time', '03:00', START + timedelta(hours=1))
    store.command(ID, 'reading', '1000.000', START + timedelta(hours=1))
    cal = store.meters[str(ID)]['calibration']
    assert cal['reading_time'] == ''
    assert cal['readings'][0]['time'] == '2026-11-01T17:00:00+00:00'
    radio(store, 1, (110, 100, 95))
    radio(store, 24, (160, 155, 150))
    store.command(ID, 'reading', '1000.300', START + timedelta(hours=24, minutes=19))
    assert 'Waiting for next transmission' in cal['status']
    radio(store, 25, (170, 160, 155))
    assert cal['solution']['factor'] == 5
    assert [r['count_interval'] for r in cal['readings']] == [[100, 110], [160, 170]]


def exact_pair(tmp_path, k=5, **options):
    store = Store(config(tmp_path, **options))
    radio(store, 0, (100, 100, 100))
    add(store, 100000, START)
    radio(store, 1, (200, 100, 100))
    cal = add(store, 100000 + k * 100, START + timedelta(hours=1))
    return store, cal


@pytest.mark.parametrize('k,method', [(5, 'standard value'), (1.234, 'fit'), (100, 'standard value')])
def test_exact_standard_and_nonstandard_fit(tmp_path, k, method):
    _, cal = exact_pair(tmp_path, k)
    assert cal['solution']['factor'] == pytest.approx(k)
    assert cal['solution']['method'] == method


def test_weighted_fit_and_residuals(tmp_path):
    store, cal = exact_pair(tmp_path, 1.234)
    radio(store, 2, (300, 200, 100))
    add(store, 100246.8, START + timedelta(hours=2))
    assert cal['solution']['factor'] == pytest.approx(1.234)
    assert all(abs(r['residual_litres']) < 1e-8 for r in cal['readings'])
    rows = [{'litres': 1000, 'count_interval': [0, 0]},
            {'litres': 1124, 'count_interval': [100, 100]},
            {'litres': 1250, 'count_interval': [180, 220]}]
    k, offset = calibration.regression(rows)
    assert k == pytest.approx(1.24003738317757, rel=1e-6)
    assert offset == pytest.approx(999.9987538940811, rel=1e-6)


def test_wrap_and_sequence_wrap(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (65520, 65520, 65520), sequence=255)
    add(store, 1000000, START)
    radio(store, 1, (40, 65520, 65520), sequence=0)
    cal = add(store, 1000280, START + timedelta(hours=1))
    assert cal['solution']['factor'] == 5
    assert cal['readings'][1]['count_interval'] == [65576, 65576]


def test_long_gap_readings_resolve_an_additional_wrap(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 1000000, START)
    radio(store, 100, (300, 290, 280))
    cal = add(store, 1000000 + (65536 + 200) * 5, START + timedelta(hours=100))
    assert cal['solution']['factor'] == 5
    assert cal['readings'][1]['count_interval'] == [65836, 65836]
    assert sum(cal['solution']['wraps'].values()) == 1


def test_ambiguous_wraps_are_not_guessed(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 1000000, START)
    radio(store, 100, (100, 100, 100))
    cal = add(store, 1000000 + 65536 * 5, START + timedelta(hours=100))
    assert cal['solution'] is None  # 5 L × one wrap, 2.5 L × two wraps, etc.
    assert 'Several' in cal['status']


@pytest.mark.parametrize('litres,reason', [(100, '1000×'), (100500000, '1000×'),
                                          (99999, 'Negative'), (123456, 'typo')])
def test_typos_units_and_negative_readings_stored_excluded_deletable(tmp_path, litres, reason):
    store, cal = exact_pair(tmp_path)
    radio(store, 2, (200, 200, 100))
    add(store, litres, START + timedelta(hours=2))
    assert not cal['readings'][-1]['used']
    assert reason in cal['readings'][-1]['reason']
    assert 'Readings disagree' in cal['status']
    assert cal['solution']['factor'] == 5
    store.command(ID, 'reading', '{"delete":3}', START + timedelta(hours=2))
    assert len(cal['readings']) == 2
    assert cal['solution']['factor'] == 5


def test_pinned_factor_offset_and_reset(tmp_path):
    store, cal = exact_pair(tmp_path, litres_per_count={'123456': 10})
    assert cal['solution']['factor'] == 10
    assert cal['solution']['method'] == 'pinned'
    assert 'disagree' in cal['status']
    store.command(ID, 'reset', 'RESET', START + timedelta(hours=2))
    assert not cal['readings']
    assert cal['solution']['factor'] == 10
    assert cal['solution']['offset'] is None
    assert store.snapshot(ID, START)['total_litres'] == 1000


@pytest.mark.parametrize('unit,value', [('m³', '1234.567'), ('kL', '1234.567'), ('L', '1234567')])
def test_plain_numbers_selected_unit_and_clear_time(tmp_path, unit, value):
    store = Store(config(tmp_path))
    store.command(ID, 'dial_unit', unit, START)
    store.command(ID, 'reading_time', '2026-11-02T02:30+10:00', START)
    store.command(ID, 'reading', value, START)
    cal = store.meters[str(ID)]['calibration']
    assert cal['readings'][0]['litres'] == 1234567
    assert cal['readings'][0]['time'] == '2026-11-01T16:30:00+00:00'
    assert cal['reading_time'] == ''
    assert store.snapshot(ID, START)['enter_reading'] == pytest.approx(float(value))


def test_json_units_explicit_past_time_and_out_of_order(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    radio(store, 1, (200, 100, 100))
    store.command(ID, 'reading', json.dumps({'kl': 100.5, 'time': (START + timedelta(hours=1)).isoformat()}),
                  START + timedelta(days=1))
    store.command(ID, 'reading', json.dumps({'m3': 100, 'time': START.isoformat(), 'source': 'photo'}),
                  START + timedelta(days=1))
    cal = store.meters[str(ID)]['calibration']
    assert cal['solution']['factor'] == 5
    assert all(r['used'] for r in cal['readings'])


@pytest.mark.parametrize('payload', ['NaN', 'Infinity', 'true', '"123"', '-1', '{}',
                                     '{"litres":1,"m3":2}', '{"litres":1,"time":"2026-01-01"}'])
def test_bad_commands_do_not_create_readings_or_consume_time(tmp_path, payload):
    store = Store(config(tmp_path))
    store.command(ID, 'reading_time', '01:00', START)
    store.command(ID, 'reading', payload, START)
    cal = store.meters[str(ID)]['calibration']
    assert not cal['readings']
    assert cal['reading_time'] == '01:00'
    assert 'Check your reading' in cal['status']


def test_minimum_usage_and_multiple_standard_values(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 10000, START)
    radio(store, 1, (110, 100, 100))
    cal = add(store, 10050, START + timedelta(hours=1))
    assert cal['solution'] is None
    assert 'Need more use' in cal['status']


def test_migrates_v1_preserves_totals_and_private_permissions(tmp_path):
    store, _ = exact_pair(tmp_path)
    path = tmp_path / 'state.json'
    state = json.loads(path.read_text())
    state['version'] = 1
    del state['meters'][str(ID)]['calibration']
    path.write_text(json.dumps(state))
    restored = Store(config(tmp_path))
    assert restored.meters[str(ID)]['total_litres'] == 0
    assert json.loads(path.read_text())['version'] == 2
    assert path.stat().st_mode & 0o777 == 0o600
    add(restored, 100000, START)
    cal = add(restored, 100500, START + timedelta(hours=1))
    assert cal['solution']['factor'] == 5


@pytest.mark.parametrize('name,value', [('dial_unit', 'gallons'), ('calibration_max_uncertainty', 0),
                                      ('calibration_max_uncertainty', float('nan')),
                                      ('calibration_min_litres', -1), ('calibration_min_litres', True)])
def test_config_validation(tmp_path, name, value):
    with pytest.raises(ValueError):
        config(tmp_path, **{name: value})


def test_later_reading_resolves_new_gap_after_calibration(tmp_path):
    store, cal = exact_pair(tmp_path)
    radio(store, 100, (400, 390, 380))
    add(store, 100500 + (65536 + 200) * 5, START + timedelta(hours=100))
    assert cal['readings'][-1]['used']
    assert cal['readings'][-1]['count_interval'] == [65936, 65936]
    assert cal['solution']['factor'] == 5
    assert store.snapshot(ID, START + timedelta(hours=100))['meter_reading'] == 429180


def test_uncalibrated_interval_width_rule_and_multiple_standards(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 10000, START)
    radio(store, 10, (200, 190, 180))
    add(store, 10300, START + timedelta(hours=9, minutes=30))
    cal = store.meters[str(ID)]['calibration']
    assert cal['solution'] is None  # [3, 3.333...], no standard, too wide.
    assert 'uncertain' in cal['status']
    # A newer exact reading makes a narrow nonstandard solution possible.
    radio(store, 11, (1100, 200, 190))
    add(store, 13100, START + timedelta(hours=11))
    assert cal['solution']['factor'] == pytest.approx(3.1)
    assert cal['solution']['method'] == 'fit'


def test_multiple_standard_sizes_need_more_usage(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 10000, START)
    radio(store, 1, (200, 100, 100))
    cal = add(store, 10500, START + timedelta(minutes=30))
    assert cal['solution'] is None  # [5, 1000]: 5, 10, 25, 50, 100 fit.
    assert 'Several' in cal['status']


def test_pending_photo_time_survives_restart_and_json_overrides_it(tmp_path):
    store = Store(config(tmp_path, timezone='Australia/Brisbane'))
    store.command(ID, 'dial_unit', 'L', START)
    store.command(ID, 'reading_time', '02:30', START)
    restored = Store(config(tmp_path, timezone='Australia/Brisbane'))
    assert restored.snapshot(ID, START)['reading_time'] == '02:30'
    assert restored.snapshot(ID, START)['dial_unit'] == 'L'
    add(restored, 100000, START)
    assert restored.meters[str(ID)]['calibration']['readings'][0]['time'] == START.astimezone(timezone.utc).isoformat()
    assert restored.snapshot(ID, START)['reading_time'] == ''


def test_offset_pin_is_respected_and_does_not_require_dial_readings(tmp_path):
    store = Store(config(tmp_path, litres_per_count={'123456': 5}, meter_reading_offset={'123456': 90000}))
    radio(store, 0, (100, 100, 100))
    assert store.snapshot(ID, START)['meter_reading'] == 90500
    cal = add(store, 123456, START)
    assert not cal['readings'][0]['used']
    assert cal['solution']['offset'] == 90000
    assert 'disagree' in cal['status']


def test_same_static_reading_needs_more_use(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 10000, START)
    radio(store, 1, (100, 100, 100))
    cal = add(store, 10000, START + timedelta(hours=1))
    assert all(r['used'] for r in cal['readings'])
    assert cal['solution'] is None
    assert 'Need more use' in cal['status']


def test_unrecoverable_photo_and_sequence_reset_are_explained(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    cal = add(store, 1000, START - timedelta(days=1))
    assert 'No counter history' in cal['status']
    radio(store, 1, (200, 100, 100), sequence=99)
    assert 'sequence changed' in cal['status']
    assert cal['solution'] is None
    store.command(ID, 'reset', 'RESET', START + timedelta(hours=1))
    assert not cal.get('blocked')
    assert not cal['slots']


def test_neighbour_scale_and_old_usage_after_guided_calibration(tmp_path):
    store, cal = exact_pair(tmp_path)
    assert store.neighbourhood_factor == 5
    assert store.snapshot(ID, START)['total_litres'] == 0
    radio(store, 2, (210, 200, 100))
    assert store.snapshot(ID, START + timedelta(hours=2))['total_litres'] == 50
    assert cal['solution']['factor'] == 5


def test_calibration_logs_are_configured_only(tmp_path, caplog):
    store = Store(config(tmp_path))
    with caplog.at_level('INFO'):
        store.command(234567, 'reading', '100', START)
        store.command(ID, 'reading', '100', START)
        store.command(ID, 'reading', 'bad json', START)
    assert '234567' not in caplog.text
    assert 'accepted' in caplog.text and 'rejected' in caplog.text
    assert all(r.levelname == 'INFO' for r in caplog.records)


@pytest.mark.parametrize('stamp', ['2026-11-02T02:50:00+10:00', '25:99', 'bad'])
def test_future_and_invalid_photo_times_explained(tmp_path, stamp):
    store = Store(config(tmp_path))
    store.command(ID, 'reading', json.dumps({'litres': 100, 'time': stamp}), START)
    cal = store.meters[str(ID)]['calibration']
    assert not cal['readings']
    assert 'Check your reading' in cal['status']


def test_gap_after_calibration_withholds_absolute_until_checked(tmp_path):
    store, cal = exact_pair(tmp_path)
    radio(store, 10, (300, 290, 280))
    assert cal['unresolved_gap']
    assert 'Counter gap may hide wraps' in cal['status']
    assert 'meter_reading' not in store.snapshot(ID, START + timedelta(hours=10))
    add(store, 101000, START + timedelta(hours=10))
    assert not cal['unresolved_gap']
    assert store.snapshot(ID, START + timedelta(hours=10))['meter_reading'] == 101000


def test_calibrated_wraps_survive_history_expiry(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 1000000, START)
    radio(store, 100, (300, 290, 280))
    cal = add(store, 1328680, START + timedelta(hours=100))
    for hour in range(101, 24 * 92):
        # Sequential static hours do not introduce any more ambiguous gaps.
        radio(store, hour, (300, 300, 300))
    assert len(cal['slots']) <= 24 * 90 + 1
    assert cal['readings'][0]['count_interval'] == [100, 100]
    assert cal['solution']['factor'] == 5
    assert store.snapshot(ID, START + timedelta(days=92))['meter_reading'] == 1328680


def test_next_transmission_uses_observed_cadence_and_local_zone(tmp_path):
    store = Store(config(tmp_path, timezone='Australia/Brisbane'))
    radio(store, 0, (100, 100, 100))
    stamp = START + timedelta(hours=1, seconds=20)
    store.frame(frame(counts=(110, 100, 100), sequence=8), stamp)
    attrs = store.snapshot(ID, stamp)['calibration']
    assert attrs['transmit_interval_seconds'] == 3620
    assert attrs['next_transmission'] == '2026-11-02T04:41:40+10:00'
    assert attrs['next_transmission_expected'] == 'Next transmission expected ≈ 04:41'


def test_unique_factor_applies_even_if_wrap_placement_between_readings_is_ambiguous(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 1000000, START)
    radio(store, 50, (200, 190, 180))
    radio(store, 100, (300, 290, 280))
    cal = add(store, 1328680, START + timedelta(hours=100))
    assert cal['solution']['factor'] == 5
    assert store.snapshot(ID, START + timedelta(hours=100))['meter_reading'] == 1328680
    # A later-entered photo disambiguates which gap actually contained the wrap.
    cal = add(store, 1328180, START + timedelta(hours=50))
    assert all(r['used'] for r in cal['readings'])
    assert cal['solution']['factor'] == 5
    assert cal['readings'][-1]['count_interval'] == [65736, 65736]


def test_offset_pin_without_dial_readings_still_withholds_new_gap(tmp_path):
    store = Store(config(tmp_path, litres_per_count={'123456': 5}, meter_reading_offset={'123456': 90000}))
    radio(store, 0, (100, 100, 100))
    assert store.snapshot(ID, START)['meter_reading'] == 90500
    radio(store, 10, (200, 190, 180))
    assert 'meter_reading' not in store.snapshot(ID, START + timedelta(hours=10))
    cal = add(store, 91000, START + timedelta(hours=10))
    assert cal['solution']['factor'] == 5
    assert store.snapshot(ID, START + timedelta(hours=10))['meter_reading'] == 91000


def test_clock_time_later_than_now_means_yesterday():
    zone = ZoneInfo('Australia/Brisbane')
    now = datetime(2026, 11, 2, 14, 5, tzinfo=timezone.utc)  # 00:05 on 3 Nov in Brisbane
    assert calibration.timestamp('23:50', now, zone) == datetime(2026, 11, 2, 13, 50, tzinfo=timezone.utc)


def test_attributes_keep_only_recent_readings():
    cal = calibration.initial()
    cal['readings'] = [{'id': i} for i in range(1, 26)]
    attrs = calibration.attributes(cal, datetime(2026, 11, 2, tzinfo=timezone.utc), ZoneInfo('Australia/Brisbane'))
    assert [r['id'] for r in attrs['readings']] == list(range(16, 26)) and attrs['reading_count'] == 25
