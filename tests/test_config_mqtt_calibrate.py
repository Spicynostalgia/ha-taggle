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
    configs = [json.loads(v) for v in configs]
    assert len(configs) == 9
    assert len({tuple(v['device']['identifiers']) for v in configs}) == 1
    water = next(c for c in configs if c['name'] == 'Water total litres')
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
    assert len(removals) == 3


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
