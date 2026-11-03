"""Synthetic replay derived from the 2–3 November 2026 overnight soak.

Only rounded times, hourly deltas and counters are retained: no capture bytes,
real transmitter IDs, private checkpoint or MQTT log are needed to run this.
Neighbour phases/cadence are regularised and their counters are invented.
"""
import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from taggle_rx import calibration, mqtt, store
from taggle_rx.mqtt import Publisher
from taggle_rx.store import Store

from .test_store import config, frame

ID = 123456
BASE = f'taggle/{ID}'
MIDNIGHT = datetime.fromisoformat('2026-11-03T00:00:00+10:00')
# Local frame times and raw counters reconstructed from hourly history. The
# overnight cadence advances about 13 s/h, then wanders slightly during the day.
HOURLY = (
    ('2026-11-02T18:41:17+10:00', 46318),
    ('2026-11-02T19:40:46+10:00', 46323),
    ('2026-11-02T20:40:26+10:00', 46330),
    ('2026-11-02T21:40:19+10:00', 46332),
    ('2026-11-02T22:40:11+10:00', 46334),
    ('2026-11-02T23:40:00+10:00', 46334),
    ('2026-11-03T00:39:29+10:00', 46334),
    ('2026-11-03T01:39:22+10:00', 46334),
    ('2026-11-03T02:39:10+10:00', 46334),
    ('2026-11-03T03:38:55+10:00', 46334),
    ('2026-11-03T04:38:44+10:00', 46334),
    ('2026-11-03T05:38:31+10:00', 46334),
    ('2026-11-03T06:38:19+10:00', 46365),
    ('2026-11-03T07:38:12+10:00', 46375),
    ('2026-11-03T08:37:54+10:00', 46423),
    ('2026-11-03T09:37:48+10:00', 46466),
    ('2026-11-03T10:38:07+10:00', 46466),
    ('2026-11-03T11:38:30+10:00', 46466),
    ('2026-11-03T12:38:35+10:00', 46468),
    ('2026-11-03T13:38:30+10:00', 46468),
    ('2026-11-03T14:38:38+10:00', 46470),
    ('2026-11-03T15:38:42+10:00', 46471),
)


def meter_frames():
    previous, older = 46283, 46279
    for index, (stamp, raw) in enumerate(HOURLY):
        yield datetime.fromisoformat(stamp), frame(
            sequence=(240 + index) % 256, counts=(raw, previous, older))
        older, previous = previous, raw


def neighbour_frames():
    # Three early-morning phases and six-hour deltas derived from the soak.
    # Their sixth new-day intervals arrive at 05:02:58, 05:03:49 and 05:04:45.
    profiles = (
        (234567, 243, (1, 18, 2, 0, 0, 1)),
        (345678, 294, (0, 0, 1, 0, 0, 1)),
        (456789, 350, (2, 2, 2, 2, 3, 2)),
    )
    for identifier, phase, deltas in profiles:
        previous, older = 1000, 999
        for hour in range(-6, 16):
            delta = deltas[hour] if 0 <= hour < 6 else 1
            raw = previous + delta
            stamp = MIDNIGHT + timedelta(seconds=phase + hour * 3587)
            yield stamp, frame(identifier=identifier, sequence=(100 + hour) % 256,
                               counts=(raw, previous, older))
            older, previous = previous, raw


@pytest.fixture
def receiver(tmp_path, monkeypatch):
    replay = SimpleNamespace(now=MIDNIGHT - timedelta(days=1), event='startup', messages=[], latest={})

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return replay.now.astimezone(tz)

    for module in (store, calibration, mqtt):
        monkeypatch.setattr(module, 'datetime', Clock)
    client = Mock()
    client.is_connected.return_value = True

    def publish(topic, payload, **options):
        assert options == {'qos': 1, 'retain': True}
        replay.messages.append((replay.now, replay.event, topic, payload))
        replay.latest[topic] = payload

    client.publish.side_effect = publish
    replay.publisher = Publisher(config(tmp_path, timezone='Australia/Brisbane'), client)
    replay.store = Store(replay.publisher.config, replay.publisher)
    replay.client = client
    replay.json = lambda topic: json.loads(replay.latest[topic])

    def reading(payload):
        replay.publisher.on_message(client, None, SimpleNamespace(
            topic=f'{BASE}/reading/set', payload=payload.encode(), retain=False))

    replay.reading = reading
    return replay


def test_overnight_replay_all_publish_paths_midnight_cohort_and_drift(receiver):
    replay = receiver
    frames = list(meter_frames())
    events = [(stamp, 'frame', decoded) for stamp, decoded in frames]
    events += [(stamp, 'neighbour', decoded) for stamp, decoded in neighbour_frames()]
    for stamp, _ in frames:
        events += [(stamp + timedelta(seconds=599), 'before_expiry', None),
                   (stamp + timedelta(minutes=10), 'expiry', None)]
    # Reading entries on either side of the daily neighbourhood warm-up exercise
    # BUG 10 through the real MQTT command callback, including a valid zero ratio.
    for clock in ('02:39:00', '05:39:00', '06:39:00'):
        when = datetime.fromisoformat(f'2026-11-03T{clock}+10:00')
        events.append((when, 'reading', json.dumps({'litres': 1597946, 'time':
                                                  '2026-11-03T02:39:00+10:00'})))
    tick = frames[0][0].replace(second=46)
    finish = frames[-1][0] + timedelta(minutes=11)
    while tick <= finish:
        events.append((tick, 'refresh', None))
        tick += timedelta(minutes=1)

    frame_states, refresh_states, neighbour_states, predictions = {}, {}, [], []
    for stamp, event, payload in sorted(events, key=lambda item: item[0]):
        replay.now, replay.event = stamp, event
        before = len(replay.messages)
        if event in ('frame', 'neighbour'):
            replay.store.frame(payload, stamp)
        elif event == 'reading':
            replay.reading(payload)
        elif event in ('expiry', 'before_expiry'):
            replay.store.expire_read_windows(stamp)
        else:
            replay.store.refresh(stamp)
        if event in ('neighbour', 'before_expiry'):
            assert len(replay.messages) == before
            continue
        state = replay.json(f'{BASE}/state')
        assert replay.latest[f'{BASE}/available'] == 'online'
        assert replay.latest[f'{BASE}/counts_available'] == 'online'
        if event == 'frame':
            frame_states[stamp] = state
            window = replay.json(f'{BASE}/read_dial_now')
            assert window['state'] == 'ON'
            assert datetime.fromisoformat(window['since']) == stamp
            assert datetime.fromisoformat(window['until']) == stamp + timedelta(minutes=10)
            attrs = replay.json(f'{BASE}/calibration')
            predictions.append(datetime.fromisoformat(attrs['next_transmission']))
            assert predictions[-1] - stamp == timedelta(seconds=attrs['transmit_interval_seconds'])
        elif event == 'expiry':
            assert len(replay.messages) > before
            assert replay.json(f'{BASE}/read_dial_now')['state'] == 'OFF'
            # Calling expiry twice must not publish twice.
            count = len(replay.messages)
            replay.store.expire_read_windows(stamp)
            assert len(replay.messages) == count
        elif event == 'refresh':
            refresh_states[stamp] = state
            neighbour_states.append((stamp, replay.json('taggle/neighbourhood/state')))

    # Check every serialized meter publication, including short-lived expiry and
    # command states, rather than just the final snapshot or Publisher.latest.
    warmup = MIDNIGHT + timedelta(hours=5, minutes=4, seconds=45)
    by_path = {path: [] for path in ('frame', 'refresh', 'expiry', 'reading')}
    for stamp, path, topic, payload in replay.messages:
        if topic == f'{BASE}/state':
            state = json.loads(payload)
            assert 'vs_neighbourhood_today' in state, (stamp, path)
            if MIDNIGHT <= stamp < warmup:
                assert state['vs_neighbourhood_today'] is None, (stamp, path)
            elif warmup <= stamp:
                assert state['vs_neighbourhood_today'] is not None, (stamp, path)
            by_path[path].append(state['vs_neighbourhood_today'])
    for values in by_path.values():
        assert None in values
        assert any(value is not None for value in values)

    before_midnight = refresh_states[MIDNIGHT - timedelta(seconds=14)]
    after_midnight = refresh_states[MIDNIGHT + timedelta(seconds=46)]
    assert (before_midnight['today'], before_midnight['hours_observed']) == (55, 7)
    assert (after_midnight['today'], after_midnight['hours_observed']) == (0, 0)
    assert before_midnight['last_seen'] == after_midnight['last_seen']
    assert before_midnight['meter_count'] == after_midnight['meter_count']
    new_day = [(stamp, state) for stamp, state in frame_states.items() if stamp >= MIDNIGHT]
    for observed, (_, state) in enumerate(new_day, 1):
        assert state['hours_observed'] == observed
        assert state['today'] == state['raw_count'] - 46334
    # The 23:40–00:39 interval belongs to the new day even though it has zero flow.
    assert new_day[0][1]['hours_observed'] == 1
    assert (new_day[6][1]['today'], new_day[6][1]['hours_observed']) == (31, 7)
    assert (new_day[-1][1]['today'], new_day[-1][1]['hours_observed']) == (137, 16)

    for stamp, state in neighbour_states:
        if MIDNIGHT <= stamp < warmup:
            assert state['meters_heard'] == 3
            assert state['meters_counted'] is None
            assert state['average_today'] is None
            assert state['median_today'] is None
            assert refresh_states[stamp]['vs_neighbourhood_today'] is None
    first_ready = next((stamp, state) for stamp, state in neighbour_states
                       if stamp >= MIDNIGHT and state['meters_counted'] is not None)
    assert first_ready[0] == MIDNIGHT + timedelta(hours=5, minutes=4, seconds=46)
    assert first_ready[1]['meters_counted'] == 3
    assert first_ready[1]['average_today'] == pytest.approx(37 / 3, abs=.005)
    assert first_ready[1]['median_today'] == 13
    assert refresh_states[first_ready[0]]['vs_neighbourhood_today'] == 0
    assert new_day[6][1]['vs_neighbourhood_today'] == pytest.approx(31 / (40 / 3) * 100, abs=.005)

    # Overnight predictions follow the moving phase, not a fixed transmit minute.
    assert predictions[0].strftime('%H:%M') == '19:41'
    assert predictions[11].strftime('%H:%M') == '06:38'
    assert abs((predictions[11] - frames[12][0]).total_seconds()) <= 2
    assert (predictions[11] - frames[11][0]).total_seconds() == pytest.approx(3587, abs=2)


@pytest.mark.parametrize(('usage', 'expected'), [(585, 5), (575, 5), (600, 600 / 116)])
def test_soak_static_readings_over_116_counts_allow_one_pulse_only(receiver, usage, expected):
    replay = receiver
    early = datetime.fromisoformat('2026-11-02T02:41:00+10:00')
    events = [(early, 'frame', frame(sequence=224, counts=(46218, 46218, 46218))),
              (early + timedelta(hours=1), 'frame', frame(sequence=225, counts=(46218, 46218, 46218))),
              (early + timedelta(minutes=2), 'reading', '1597.361'),
              (MIDNIGHT + timedelta(hours=2, minutes=39), 'reading', f'{(1597361 + usage) / 1000:.3f}')]
    events += [(stamp, 'frame', decoded) for stamp, decoded in meter_frames()
               if stamp <= MIDNIGHT + timedelta(hours=3)]
    for stamp, event, payload in sorted(events, key=lambda item: item[0]):
        replay.now, replay.event = stamp, event
        if event == 'frame':
            replay.store.frame(payload, stamp)
        else:
            replay.reading(payload)
    attrs = replay.json(f'{BASE}/calibration')
    assert [row['count_interval'] for row in attrs['readings']] == [[46218, 46218], [46334, 46334]]
    assert attrs['readings'][1]['litres'] - attrs['readings'][0]['litres'] == usage
    assert all(row['used'] for row in attrs['readings'])
    assert attrs['chosen_k'] == pytest.approx(expected)
    assert attrs['method'] == ('standard value' if expected == 5 else 'fit')
    state = replay.json(f'{BASE}/state')
    assert state['litres_per_count'] == pytest.approx(expected, abs=.005)
    if expected == 5:
        assert 'Calibrated: 5 L per pulse' in state['calibration_status']
    # Re-solving on a minute tick and after restart must keep both readings and
    # the same factor, including when a phase allowance was needed to fit them.
    replay.now += timedelta(minutes=1)
    replay.store.refresh(replay.now)
    replay.store = Store(replay.publisher.config, replay.publisher)
    replay.store.refresh(replay.now)
    attrs = replay.json(f'{BASE}/calibration')
    assert all(row['used'] for row in attrs['readings'])
    assert attrs['chosen_k'] == pytest.approx(expected)
