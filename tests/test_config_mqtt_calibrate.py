from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from taggle_rx.calibrate import fit, main, rows
from taggle_rx.cli import main as rx_main
from taggle_rx.cli import rtl_command
from taggle_rx.config import Config
from taggle_rx.mqtt import Publisher


@pytest.mark.parametrize('raw', [
    {}, {'meter_ids': [True]}, {'meter_ids': ['bad']}, {'meter_ids': [2**20]},
    {'meter_ids': [123456], 'gain': float('nan')},
    {'meter_ids': [123456], 'sample_rate': 1000},
    {'meter_ids': [123456], 'litres_per_count': {'123456': 0}},
    {'meter_ids': [123456], 'litres_per_count': {'123456': float('inf')}},
    {'meter_ids': [123456], 'litres_per_count': {'234567': 2}},
    {'meter_ids': [123456], 'mqtt': {'topic_prefix': '#'}},
    {'meter_ids': [123456], 'log_all_meters': 'false'},
])
def test_reject_invalid_config(raw):
    with pytest.raises(ValueError):
        Config.from_dict(raw)


def test_scan_config_and_rtl_args():
    cfg = Config.from_dict({'device': 'fake-serial', 'gain': 30}, scan=True)
    assert rtl_command(cfg) == ['rtl_sdr', '-d', 'fake-serial', '-f', '922200000',
                                '-s', '2400000', '-g', '30', '-']


def test_discovery_units_reconnect_and_availability():
    cfg = Config.from_dict({'meter_ids': [123456], 'litres_per_count': {'123456': 2}})
    client = Mock()
    publisher = Publisher(cfg, client)
    publisher.on_connect(client, None, None, 0)
    configs = [args.args[1] for args in client.publish.call_args_list if args.args[0].endswith('/config')]
    import json
    configs = [json.loads(v) for v in configs if v]
    assert len(configs) == 20
    assert len({tuple(v['device']['identifiers']) for v in configs}) == 2
    water = next(c for c in configs if c['name'] == 'Total litres')
    assert water['device_class'] == 'water'
    assert water['state_class'] == 'total_increasing'
    assert water['unit_of_measurement'] == 'L'
    assert all(c.get('state_class') in (None, 'total', 'total_increasing')
               for c in configs if c.get('device_class') == 'water')
    state = {'last_seen': (datetime.now(timezone.utc)-timedelta(hours=4)).isoformat(),
             'meter_count': 10, 'encrypted': False}
    publisher.publish(123456, state)
    assert any(c.args[:2] == ('taggle/123456/available', 'offline') for c in client.publish.call_args_list)
    client.publish.reset_mock()
    publisher.on_message(client, None, Mock(topic='homeassistant/status', payload=b'online'))
    assert any(c.args[0] == 'taggle/123456/state' for c in client.publish.call_args_list)


def test_unscaled_discovery_removes_litre_entities():
    client = Mock()
    Publisher(Config.from_dict({'meter_ids': [123456]}), client).announce()
    removals = [c for c in client.publish.call_args_list if c.args[1] == '']
    assert len(removals) == 4


def test_two_readings_and_csv_fit(tmp_path, capsys):
    path = tmp_path / 'readings.csv'
    path.write_text('time,register_reading,meter_count\n2026-01-01T00:00:00Z,10,100\n2026-01-02T00:00:00Z,10.25,200\n')
    result = fit(rows(path, 'register_reading'), rows(path, 'meter_count'), 1000)
    assert result['litres_per_count'] == 2.5
    assert result['rmse_litres'] == 0
    assert main([str(path), '--register-unit', 'm3']) == 0
    assert '2.5' in capsys.readouterr().out


def test_fit_rejects_no_use_and_counter_resets():
    first = datetime(2026, 1, 1, tzinfo=timezone.utc)
    second = first + timedelta(days=1)
    with pytest.raises(ValueError):
        fit({first: 10, second: 20}, {first: 100, second: 50})
    with pytest.raises(ValueError):
        fit({first: 10, second: 10}, {first: 100, second: 150})


def test_scan_file_cli_does_not_connect_or_write(tmp_path, monkeypatch):
    import json

    import taggle_rx.cli
    monkeypatch.setattr(taggle_rx.cli, 'Publisher', Mock(side_effect=AssertionError('MQTT in scan')))
    config = tmp_path / 'options.json'
    data = tmp_path / 'data'
    config.write_text(json.dumps({'data_dir': str(data)}))
    source = tmp_path / 'empty.bin'
    source.write_bytes(b'')
    assert rx_main(['--config', str(config), '--input', str(source), '--scan', '1',
                    '--start-utc', '2026-01-01T00:00:00Z']) == 0
    assert not data.exists()


def test_cli_logs_startup_and_heartbeat_during_radio_silence(tmp_path, monkeypatch, caplog):
    import json
    import queue

    import taggle_rx.cli as cli

    now = 1000.
    calls = 0

    def read(timeout):
        nonlocal now, calls
        calls += 1
        now += 300
        if calls <= 3:
            raise queue.Empty
        return 'eof', None, None

    pump = Mock()
    pump.items.get.side_effect = read
    monkeypatch.setattr(cli.time, 'monotonic', lambda: now)
    monkeypatch.setattr(cli, 'InputPump', Mock(return_value=pump))
    monkeypatch.setattr(cli, 'Receiver', Mock())
    monkeypatch.setattr(cli, 'Publisher', Mock())
    config = tmp_path / 'options.json'
    config.write_text(json.dumps({'meter_ids': [123456, 123457], 'data_dir': str(tmp_path / 'data')}))
    source = tmp_path / 'empty.bin'
    source.write_bytes(b'')
    with caplog.at_level('INFO'):
        assert rx_main(['--config', str(config), '--input', str(source),
                        '--start-utc', '2026-01-01T00:00:00Z']) == 0
    assert caplog.messages == [
        'Listening on 922.2 MHz for meter(s): 2 configured; first reading can take up to an hour',
        'still listening: 0 frames from 0 other meters heard in the last 15 min',
    ]


@pytest.mark.parametrize('prefix', ['taggle', 'house/taggle'])
def test_discovery_entity_ids_and_name_fallback(prefix):
    from taggle_rx.mqtt import ENTITIES, NEIGHBOURHOOD_ENTITIES

    publisher = Publisher(Config.from_dict({'meter_ids': [123456], 'mqtt': {'topic_prefix': prefix}}), Mock())
    for key, spec in ENTITIES.items():
        payload = publisher.discovery(123456, key, spec)
        assert payload['default_entity_id'] == f'sensor.taggle_123456_{key}'
        assert payload['unique_id'] == f'{prefix}_123456_{key}'
        assert 'object_id' not in payload
        fallback = (payload['device']['name'] + ' ' + payload['name']).lower().replace(' ', '_')
        assert 'sensor.' + fallback == payload['default_entity_id']
    for key in NEIGHBOURHOOD_ENTITIES:
        payload = publisher.neighbourhood_discovery(key)
        assert payload['default_entity_id'] == f'sensor.taggle_neighbourhood_{key}'
        assert payload['unique_id'] == f'{prefix}_neighbourhood_{key}'
        assert 'object_id' not in payload
        fallback = (payload['device']['name'] + ' ' + payload['name']).lower().replace(' ', '_')
        assert 'sensor.' + fallback == payload['default_entity_id']


@pytest.mark.parametrize('calibrated', [False, True])
def test_discovery_display_precision(calibrated):
    from taggle_rx.mqtt import ENTITIES, NEIGHBOURHOOD_ENTITIES

    cfg = Config.from_dict({'meter_ids': [123456],
                            'litres_per_count': {'123456': 2.5} if calibrated else {}})
    publisher = Publisher(cfg, Mock())
    for key, spec in ENTITIES.items():
        payload = publisher.discovery(123456, key, spec)
        if key in ('last_seen', 'calibration_status'):
            assert 'suggested_display_precision' not in payload
        else:
            assert payload['suggested_display_precision'] == (0 if spec[1] == 'pulses' or key == 'meter_reading' else 1)
    for key in NEIGHBOURHOOD_ENTITIES:
        payload = publisher.neighbourhood_discovery(key)
        assert payload['suggested_display_precision'] == (1 if calibrated and not key.startswith('meters_') else 0)


def test_mqtt_rounds_wire_values_without_changing_state_or_attributes(tmp_path):
    import json

    from taggle_rx.store import Store

    from .test_store import config, frame

    cfg = config(tmp_path, litres_per_count={'123456': 1.234567})
    client = Mock()
    publisher = Publisher(cfg, client)
    store = Store(cfg, publisher)
    stamp = datetime.now(timezone.utc)
    decoded = {**frame(), 'snr_median_db': 30.087156629613467,
               'signal_level_dbfs': -40.90190578364269}
    store.frame(decoded, stamp)
    state = publisher.latest[123456]
    state['vs_neighbourhood_today'] = 123.456789
    original = dict(state)
    for action in (lambda: publisher.publish(123456, state), publisher.announce):
        client.publish.reset_mock()
        action()
        wire = next(json.loads(c.args[1]) for c in client.publish.call_args_list
                    if c.args[0] == 'taggle/123456/state')
        assert wire['snr'] == 30.09
        assert wire['signal_level'] == -40.90
        assert wire['last_hour_litres'] == 12.35
        assert wire['today_litres'] == wire['total_litres'] == 19.75
        assert wire['vs_neighbourhood_today'] == 123.46
        assert wire['last_hour'] == 10
        assert wire['last_seen'] == stamp.isoformat()
        attrs = next(json.loads(c.args[1]) for c in client.publish.call_args_list
                     if c.args[0] == 'taggle/123456/attributes')
        assert attrs['litres_per_count'] == 1.234567
        assert attrs['history'] == state['history']
        assert state == original
    stored = json.loads((tmp_path / 'state.json').read_text())['meters']['123456']
    assert stored['snr'] == decoded['snr_median_db']
    assert stored['signal_level'] == decoded['signal_level_dbfs']
    assert stored['total_litres'] == 16 * 1.234567

    aggregate = dict(meters_heard=3, meters_counted=None, average_today=1.234567,
                     median_today=3.456789, average_last_hour=5.678901)
    publisher.publish_neighbourhood(aggregate)
    for action in (lambda: publisher.publish_neighbourhood(aggregate), publisher.announce):
        client.publish.reset_mock()
        action()
        wire = next(json.loads(c.args[1]) for c in client.publish.call_args_list
                    if c.args[0] == 'taggle/neighbourhood/state')
        assert wire == dict(meters_heard=3, meters_counted=None, average_today=1.23,
                            median_today=3.46, average_last_hour=5.68)
    assert aggregate['average_today'] == 1.234567


def test_mqtt_connection_logs_only_broker_address(caplog):
    cfg = Config.from_dict({'meter_ids': [123456], 'mqtt': {
        'host': 'broker.local', 'port': 1884, 'username': 'private-user', 'password': 'private-password'}})
    client = Mock()
    publisher = Publisher(cfg, client)
    with caplog.at_level('INFO'):
        publisher.on_connect(client, None, None, 5)
        assert not caplog.records
        publisher.on_connect(client, None, None, 0)
        publisher.on_disconnect(client, None, None, 0)
        publisher.on_connect(client, None, None, 0)
        publisher.on_disconnect(client, None, None, 7)
    assert caplog.messages == ['MQTT connected to broker.local:1884',
                               'MQTT disconnected from broker.local:1884'] * 2
    assert client.on_disconnect == publisher.on_disconnect
    assert 'private-user' not in caplog.text
    assert 'private-password' not in caplog.text


def test_file_cli_refreshes_wall_clock_state_after_flush(tmp_path, monkeypatch):
    import json

    import taggle_rx.cli as cli

    from .test_store import frame

    now = datetime(2026, 1, 2, 0, 30, tzinfo=timezone.utc)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz)

    publisher = Mock()
    monkeypatch.setattr(cli, 'datetime', Clock)
    monkeypatch.setattr(cli, 'Publisher', Mock(return_value=publisher))

    def receiver(store, *args):
        rx = Mock()
        flushed = False

        def flush():
            nonlocal flushed
            if not flushed:
                flushed = True
                stamp = now - timedelta(hours=1)
                store.frame(frame(), stamp)
                for identifier in (234567, 234568, 234569):
                    store.frame(frame(identifier=identifier, size=24), stamp)
        rx.flush.side_effect = flush
        return rx

    monkeypatch.setattr(cli, 'Receiver', receiver)
    config = tmp_path / 'options.json'
    config.write_text(json.dumps({'meter_ids': [123456], 'data_dir': str(tmp_path / 'data')}))
    source = tmp_path / 'empty.bin'
    source.write_bytes(b'')
    assert rx_main(['--config', str(config), '--input', str(source),
                    '--start-utc', '2026-01-01T23:30:00Z']) == 0
    assert next(c.args[1] for c in publisher.publish.call_args_list if 'today' in c.args[1])['today'] == 16
    final = publisher.publish.call_args.args[1]
    assert final['today'] == 0
    assert final['last_seen'] == '2026-01-01T23:30:00+00:00'
    assert publisher.publish_neighbourhood.call_args.args[0]['meters_heard'] == 3
    assert publisher.method_calls[-1][0] == 'close'


def test_auto_calibrated_discovery_and_neighbour_units_survive_opaque_frames(tmp_path):
    import json

    from taggle_rx.store import Store

    from .test_guided_calibration import START, add, radio
    from .test_store import config, frame

    cfg = config(tmp_path)
    client = Mock()
    publisher = Publisher(cfg, client)
    store = Store(cfg, publisher)
    radio(store, 0, (100, 100, 100))
    add(store, 100000, START)
    radio(store, 1, (200, 100, 100))
    add(store, 100500, START + timedelta(hours=1))
    store.frame(frame(size=24), START + timedelta(hours=2))
    assert store.neighbourhood_factor == publisher.neighbourhood_factor == 5
    client.publish.reset_mock()
    publisher.announce()
    configs = {c.args[0]: json.loads(c.args[1]) for c in client.publish.call_args_list
               if c.args[0].endswith('/config') and c.args[1]}
    assert configs['homeassistant/sensor/taggle_123456/total_litres/config']['unit_of_measurement'] == 'L'
    assert configs['homeassistant/sensor/taggle_neighbourhood/average_today/config']['unit_of_measurement'] == 'L'
