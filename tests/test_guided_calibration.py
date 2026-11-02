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
    assert cal['bounds'] == pytest.approx([402 / 100, 406 / 65])
    solution = cal['solution']
    assert solution['factor'] == 5
    assert solution['method'] == 'standard value'
    assert solution['offset'] == 1597361 - 46218 * 5
    assert cal['readings'][1]['count_interval'] == [46283, 46318]
    assert all(r['used'] for r in cal['readings'])
    state = store.snapshot(ID, second + timedelta(hours=1))
    assert state['meter_reading'] == 1597861
    assert state['calibration']['next_transmission_expected'] == 'Next transmission expected ≈ 19:41'
    assert 'within 10 minutes' in state['calibration']['guidance']
    restored = Store(config(tmp_path, timezone='Australia/Brisbane'))
    assert restored.meters[str(ID)]['calibration']['solution'] == json.loads(json.dumps(solution))
    assert restored.snapshot(ID, second)['meter_reading'] == state['meter_reading']
    # Synthetic follow-up checks validation; the real 3 November utility reading is not supplied.
    radio(restored, 40, (46418, 46418, 46418))
    cal = add(restored, 1598361, START + timedelta(hours=40))
    assert cal['readings'][-1]['used']
    assert cal['readings'][-1]['residual_litres'] == pytest.approx(0, abs=1)


def test_manual_only_two_mid_hour_readings_and_photo_time(tmp_path):
    store = Store(config(tmp_path, timezone='Australia/Brisbane'))
    radio(store, 0, (100, 95, 90))
    store.command(ID, 'reading', '1000.000 03:00', START + timedelta(hours=1))
    cal = store.meters[str(ID)]['calibration']
    assert 'reading_time' not in cal
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
    assert 'fit' in cal['status']


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
def test_selected_unit_and_attached_photo_time(tmp_path, unit, value):
    store = Store(config(tmp_path))
    store.command(ID, 'dial_unit', unit, START)
    store.command(ID, 'reading', value + ' 2026-11-02T02:30+10:00', START)
    cal = store.meters[str(ID)]['calibration']
    assert cal['readings'][0]['litres'] == 1234567
    assert cal['readings'][0]['time'] == '2026-11-01T16:30:00+00:00'
    assert 'reading_time' not in cal
    assert store.snapshot(ID, START)['dial_reading'] == value + ' 2026-11-02T02:30+10:00'


def test_json_units_explicit_past_time_and_out_of_order(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    radio(store, 1, (200, 100, 100))
    store.command(ID, 'reading', f'{{"kl":100.500,"time":"{(START + timedelta(hours=1)).isoformat()}"}}',
                  START + timedelta(days=1))
    store.command(ID, 'reading', f'{{"m3":100.000,"time":"{START.isoformat()}","source":"photo"}}',
                  START + timedelta(days=1))
    cal = store.meters[str(ID)]['calibration']
    assert cal['solution']['factor'] == 5
    assert all(r['used'] for r in cal['readings'])


@pytest.mark.parametrize('payload', ['NaN', 'Infinity', 'true', '"123"', '-1', '{}',
                                     '{"litres":1,"m3":2}', '{"litres":1,"time":"2026-01-01"}'])
def test_bad_commands_do_not_create_readings(tmp_path, payload):
    store = Store(config(tmp_path))
    store.command(ID, 'reading', payload, START)
    cal = store.meters[str(ID)]['calibration']
    assert not cal['readings']
    assert 'reading_time' not in cal
    assert 'Check your reading' in cal['status']


def test_small_usage_calibrates_without_a_gate(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 10000, START)
    radio(store, 1, (110, 100, 100))
    cal = add(store, 10050, START + timedelta(hours=1))
    assert cal['solution']['factor'] == 5


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
                                      ('calibration_max_uncertainty', float('nan'))])
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
    assert cal['solution']['factor'] == pytest.approx(3.1, abs=.0001)
    assert cal['solution']['method'] == 'fit'


def test_multiple_standard_sizes_need_more_usage(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 10000, START)
    radio(store, 1, (200, 100, 100))
    cal = add(store, 10500, START + timedelta(minutes=30))
    assert cal['solution'] is None  # [5, 1000]: 5, 10, 25, 50, 100 fit.
    assert 'fit' in cal['status']


def test_pending_photo_time_is_dropped_during_state_migration(tmp_path):
    store = Store(config(tmp_path, timezone='Australia/Brisbane'))
    store.command(ID, 'dial_unit', 'L', START)
    store.meters[str(ID)]['calibration']['reading_time'] = '02:30'
    store.save()
    restored = Store(config(tmp_path, timezone='Australia/Brisbane'))
    assert 'reading_time' not in restored.snapshot(ID, START)
    assert 'reading_time' not in restored.meters[str(ID)]['calibration']
    assert 'reading_time' not in json.loads((tmp_path / 'state.json').read_text())['meters'][str(ID)]['calibration']
    assert restored.snapshot(ID, START)['dial_unit'] == 'L'
    add(restored, 100000, START)
    assert restored.meters[str(ID)]['calibration']['readings'][0]['time'] == START.astimezone(timezone.utc).isoformat()


def test_offset_pin_is_respected_and_does_not_require_dial_readings(tmp_path):
    store = Store(config(tmp_path, litres_per_count={'123456': 5}, meter_reading_offset={'123456': 90000}))
    radio(store, 0, (100, 100, 100))
    assert store.snapshot(ID, START)['meter_reading'] == 90500
    cal = add(store, 123456, START)
    assert not cal['readings'][0]['used']
    assert cal['solution']['offset'] == 90000
    assert 'disagree' in cal['status']


def test_two_exact_static_readings_explain_no_water_used(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 10000, START)
    radio(store, 1, (100, 100, 100))
    cal = add(store, 10000, START + timedelta(hours=1))
    assert all(r['used'] for r in cal['readings'])
    assert cal['solution'] is None
    assert 'No water was used between your readings' in cal['status']


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


@pytest.mark.parametrize('payload,clock', [
    ('1597.765', '02:41'), ('1597,765', '02:41'),
    ('1597.765 02:30', '02:30'), ('1597.765 2:30', '02:30'),
    ('1597.765 0230', '02:30'), ('1597.765 at 02:30', '02:30'),
    ('1597,765@02:30', '02:30'), ('1597.765 @ 0230', '02:30'),
    ('1597.765 1800', '18:00'), ('1597.765 at 1800', '18:00'),
    ('1597.765@2026-11-02T02:30:00+10:00', '02:30'),
    ('1597.765 2026-11-02T02:30:00+1000', '02:30'),
    ('1597.765 2026-11-01T16:30:00Z', '02:30'),
    ('{"m3":1597.765,"time":"0230"}', '02:30'),
])
def test_single_box_formats(tmp_path, payload, clock):
    store = Store(config(tmp_path, timezone='Australia/Brisbane'))
    store.command(ID, 'reading', payload, START)
    row = store.meters[str(ID)]['calibration']['readings'][0]
    assert row['litres'] == 1597765
    stamp = datetime.fromisoformat(row['time']).astimezone(store.zone)
    assert stamp.strftime('%H:%M') == clock
    assert stamp.day == (1 if clock == '18:00' else 2)
    assert row['resolution_litres'] == 1


@pytest.mark.parametrize('payload', ['1597.765 2500', '1597.765 18:99', '1597.765 180',
    '1597.765 at', '1597.765@@18:00', '1597.765 18:00 extra', '1597.76518:00',
    '1,597.765', '1.597,765', '1597 L', '', '18:00', '1597.765 2026-11-01T18:00',
    '1597.765 2026-99-01T18:00+10:00'])
def test_single_box_rejects_bad_input_without_affecting_next_reading(tmp_path, payload):
    store = Store(config(tmp_path))
    store.command(ID, 'reading', payload, START)
    cal = store.meters[str(ID)]['calibration']
    assert not cal['readings'] and 'Check your reading' in cal['status']
    store.command(ID, 'reading', '1597.765', START)
    assert datetime.fromisoformat(cal['readings'][0]['time']) == START


@pytest.mark.parametrize('value,unit,resolution', [
    ('1597.765', 'm³', 1), ('1597.76', 'm³', 10), ('1597', 'm³', 1000),
    ('1597.765', 'kL', 1), ('1597765', 'L', 1), ('1597765.5', 'L', .1), ('1597.7654', 'm³', .1), ('1597,76', 'kL', 10),
    ('{"m3":1597.760}', 'L', 1), ('{"m3":1597.76}', 'L', 10),
])
def test_dial_resolution_follows_typed_decimals(tmp_path, value, unit, resolution):
    store = Store(config(tmp_path))
    store.command(ID, 'dial_unit', unit, START)
    store.command(ID, 'reading', value, START)
    assert store.meters[str(ID)]['calibration']['readings'][0]['resolution_litres'] == resolution


@pytest.mark.parametrize('pulses,usage', [(2, 9), (2, 11), (1, 5), (1, 6)])
def test_one_hour_small_exact_pair_with_one_litre_misread_snaps_to_five(tmp_path, pulses, usage):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 100000, START)
    radio(store, 1, (100 + pulses, 100, 100))
    cal = add(store, 100000 + usage, START + timedelta(hours=1))
    assert all(r['exact'] for r in cal['readings'])
    assert cal['solution']['factor'] == 5
    assert 'Calibrated: 5 L' in cal['status']
    assert all(abs(r['residual_litres']) <= 1 for r in cal['readings'])


def test_four_hour_small_usage_names_ambiguous_sizes_then_third_calibrates(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    first = START + timedelta(minutes=30)
    add(store, 100000, first)
    radio(store, 1, (100, 100, 100))
    radio(store, 4, (102, 101, 100))
    second = first + timedelta(hours=4)
    add(store, 100020, second)
    radio(store, 5, (104, 102, 101))
    cal = store.meters[str(ID)]['calibration']
    assert cal['solution'] is None
    assert '5 L and 10 L per pulse both fit' in cal['status']
    assert 'just after the next transmission (≈' in cal['status']
    radio(store, 6, (108, 104, 102))
    add(store, 100040, START + timedelta(hours=6))
    assert cal['solution']['factor'] == 5


def test_read_now_window_and_step_texts_refresh_without_new_frames(tmp_path):
    store = Store(config(tmp_path))
    store.command(ID, 'dial_unit', 'L', START)
    assert 'Step 1 of 3 — wait' in store.snapshot(ID, START)['calibration_status']
    assert store.snapshot(ID, START)['read_dial_now']['state'] == 'OFF'
    radio(store, 0, (100, 100, 100))
    for minutes in (0, 5, 9.99):
        state = store.snapshot(ID, START + timedelta(minutes=minutes))
        assert state['read_dial_now']['state'] == 'ON'
        assert 'Read your dial now' in state['calibration_status']
        assert state['read_dial_now']['since'] == START.astimezone(timezone.utc).isoformat()
        assert datetime.fromisoformat(state['read_dial_now']['until']) == START + timedelta(minutes=10)
        assert state['read_dial_now']['next_transmission']
    assert store.snapshot(ID, START + timedelta(minutes=10))['read_dial_now']['state'] == 'OFF'
    assert 'Step 1 of 3 — wait' in store.snapshot(ID, START + timedelta(minutes=11))['calibration_status']
    add(store, 100000, START)
    state = store.snapshot(ID, START + timedelta(minutes=11))
    assert 'Step 2 of 3' in state['calibration_status'] and '20–50 L' in state['calibration_status']
    radio(store, 1, (104, 100, 100))
    assert 'Step 3 of 3' in store.snapshot(ID, START + timedelta(hours=1))['calibration_status']
    add(store, 100020, START + timedelta(hours=1))
    assert 'Calibrated: 5 L' in store.snapshot(ID, START + timedelta(hours=1))['calibration_status']


def test_exact_flag_requires_window_and_static_bracket(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    cal = add(store, 100000, START + timedelta(minutes=2))
    assert not cal['readings'][0]['exact']  # Next boundary not known yet.
    radio(store, 1, (100, 100, 100))
    assert cal['readings'][0]['exact']
    add(store, 100000, START + timedelta(minutes=10))
    assert not cal['readings'][-1]['exact']  # Exactly ten minutes closes the window.
    add(store, 100000, START + timedelta(hours=1, minutes=2))
    radio(store, 2, (101, 100, 100))
    assert not cal['readings'][-1]['exact']  # Pulses in the bracket; don't assume timing.
    # Recovered slots without a received frame don't open an exactness window.
    add(store, 100000, START - timedelta(hours=1))
    assert not cal['readings'][-1]['exact']


def test_retired_and_unknown_saved_options_warn_and_do_not_block_startup(tmp_path, caplog):
    cfg = config(tmp_path, calibration_min_litres=200, retired_option='old')
    Store(cfg)
    assert 'Ignoring unknown option calibration_min_litres' in caplog.text
    assert 'Ignoring unknown option retired_option' in caplog.text
    assert not hasattr(cfg, 'calibration_min_litres')


@pytest.mark.parametrize('clock', ['02:30', '2:30', '0230'])
@pytest.mark.parametrize('now', [datetime(2026, 3, 8, 8, tzinfo=timezone.utc),
                                 datetime(2026, 11, 1, 8, tzinfo=timezone.utc)])
def test_clock_formats_keep_dst_guards(clock, now):
    # New York jumps over 02:30 in March; 01:30 occurs twice in November.
    clock = clock.replace('2', '1') if now.month == 11 else clock
    with pytest.raises(ValueError, match='does not exist|occurs twice'):
        calibration.timestamp(clock, now, ZoneInfo('America/New_York'))


def test_read_window_publishes_off_at_deadline_during_radio_silence(tmp_path):
    from unittest.mock import Mock

    publisher = Mock()
    store = Store(config(tmp_path), publisher)
    radio(store, 0, (100, 100, 100))
    assert publisher.publish.call_args.args[1]['read_dial_now']['state'] == 'ON'
    publisher.publish.reset_mock()
    store.expire_read_windows(START + timedelta(minutes=9, seconds=59))
    publisher.publish.assert_not_called()
    store.expire_read_windows(START + timedelta(minutes=10))
    assert publisher.publish.call_args.args[1]['read_dial_now']['state'] == 'OFF'
    publisher.publish.reset_mock()
    store.expire_read_windows(START + timedelta(minutes=11))
    publisher.publish.assert_not_called()


def test_new_configured_frame_extends_window_but_neighbours_do_not(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    store.frame(frame(identifier=234567), START + timedelta(minutes=9))
    assert store.snapshot(ID, START + timedelta(minutes=10))['read_dial_now']['state'] == 'OFF'
    radio(store, 1, (101, 100, 100))
    assert store.snapshot(ID, START + timedelta(hours=1, minutes=9))['read_dial_now']['state'] == 'ON'
    assert store.snapshot(ID, START + timedelta(hours=1, minutes=10))['read_dial_now']['state'] == 'OFF'


def test_one_pulse_four_litres_keeps_both_standard_sizes_with_resolution(tmp_path):
    store = Store(config(tmp_path))
    radio(store, 0, (100, 100, 100))
    add(store, 100000, START)
    radio(store, 1, (101, 100, 100))
    cal = add(store, 100004, START + timedelta(hours=1))
    # ±1 L per reading gives ΔL in [2, 6]; neither candidate can be discarded.
    assert cal['bounds'] == [2, 6]
    assert cal['solution'] is None
    assert '2.5 L and 5 L per pulse both fit' in cal['status']
    radio(store, 2, (104, 101, 100))
    add(store, 100020, START + timedelta(hours=2))
    assert cal['solution']['factor'] == 5


def test_attached_photo_time_cannot_leak_into_the_next_reading(tmp_path):
    store = Store(config(tmp_path, timezone='Australia/Brisbane'))
    first_submission = START + timedelta(hours=16)
    store.command(ID, 'reading', '1597.765 18:00', first_submission)
    second_submission = first_submission + timedelta(minutes=10)
    store.command(ID, 'reading', '1597.770', second_submission)
    rows = store.meters[str(ID)]['calibration']['readings']
    assert datetime.fromisoformat(rows[0]['time']).astimezone(store.zone).strftime('%H:%M') == '18:00'
    assert datetime.fromisoformat(rows[1]['time']) == second_submission
    assert 'reading_time' not in store.meters[str(ID)]['calibration']
