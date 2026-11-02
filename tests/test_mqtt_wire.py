"""Exercise the real Paho client against an isolated minimal MQTT 3.1.1 broker."""
import json
import socket
import threading
import time

from taggle_rx.config import Config
from taggle_rx.mqtt import Publisher


def packet(source):
    header = source.recv(1)
    if not header:
        raise EOFError
    length, multiplier = 0, 1
    while True:
        value = source.recv(1)[0]
        length += (value & 127) * multiplier
        if not value & 128:
            break
        multiplier *= 128
    body = bytearray()
    while len(body) < length:
        data = source.recv(length - len(body))
        if not data:
            raise EOFError
        body.extend(data)
    return header[0], body


class Broker:
    def __init__(self):
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen()
        self.listener.settimeout(.2)
        self.port = self.listener.getsockname()[1]
        self.records = []
        self.connections = 0
        self.subscriptions = []
        self.stopping = threading.Event()
        self.condition = threading.Condition()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.source = None
        self.thread.start()

    def run(self):
        while not self.stopping.is_set():
            try:
                source, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            self.source = source
            try:
                header, _ = packet(source)
                assert header >> 4 == 1
                source.sendall(b'\x20\x02\x00\x00')
                self.connections += 1
                while not self.stopping.is_set():
                    header, body = packet(source)
                    kind = header >> 4
                    if kind == 8:
                        size = int.from_bytes(body[2:4], 'big')
                        self.subscriptions.append(body[4:4+size].decode())
                        source.sendall(b'\x90\x03' + body[:2] + b'\x01')
                    elif kind == 3:
                        size = int.from_bytes(body[:2], 'big')
                        topic = body[2:2+size].decode()
                        offset = 2+size
                        if (header >> 1) & 3:
                            source.sendall(b'\x40\x02' + body[offset:offset+2])
                            offset += 2
                        with self.condition:
                            self.records.append((topic, body[offset:].decode()))
                            self.condition.notify_all()
                    elif kind == 12:
                        source.sendall(b'\xd0\x00')
                    elif kind == 14:
                        break
            except (OSError, EOFError):
                pass
            finally:
                source.close()

    def wait(self, predicate):
        deadline = time.monotonic() + 6
        with self.condition:
            while not predicate(self.records):
                remaining = deadline - time.monotonic()
                assert remaining > 0, 'timed out waiting for MQTT publication'
                self.condition.wait(min(.1, remaining))

    def send(self, topic, payload, retain=False):
        topic = topic.encode()
        body = len(topic).to_bytes(2, 'big') + topic + payload.encode()
        size = len(body)
        encoded = bytearray()
        while True:
            byte, size = size % 128, size // 128
            encoded.append(byte | (128 if size else 0))
            if not size:
                break
        self.source.sendall(bytes([0x31 if retain else 0x30]) + encoded + body)

    def close(self):
        self.stopping.set()
        if self.source:
            try:
                self.source.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.listener.close()
        self.thread.join(timeout=2)


def test_real_paho_discovery_state_reconnect_and_graceful_offline():
    broker = Broker()
    config = Config.from_dict({'meter_ids': [123456], 'mqtt': {'host': '127.0.0.1', 'port': broker.port}})
    publisher = Publisher(config)
    try:
        publisher.publish(123456, {'last_seen': '2026-01-01T00:00:00+00:00',
                                   'encrypted': False, 'meter_count': 16, 'today': 16,
                                   'last_hour': 10, 'snr': 20, 'signal_level': -35})
        publisher.start()
        broker.wait(lambda rows: ('taggle/status', 'online') in rows)
        state = next(json.loads(payload) for topic, payload in broker.records if topic == 'taggle/123456/state')
        assert state['meter_count'] == 16
        assert any(topic.endswith('/last_seen/config') for topic, _ in broker.records)
        broker.source.shutdown(socket.SHUT_RDWR)
        broker.wait(lambda rows: broker.connections >= 2 and sum(topic == 'taggle/123456/state' for topic, _ in rows) >= 2)
        before = len(broker.records)
        topic = b'homeassistant/status'
        body = len(topic).to_bytes(2, 'big') + topic + b'online'
        broker.source.sendall(bytes([0x30, len(body)]) + body)
        broker.wait(lambda rows: any(topic.endswith('/last_seen/config') for topic, _ in rows[before:]))
        publisher.close()
        broker.wait(lambda rows: ('taggle/status', 'offline') in rows)
    finally:
        publisher.close()
        broker.close()


def test_guided_commands_over_real_mqtt_reconnect_birth_and_reset(tmp_path, monkeypatch):
    from datetime import datetime, timedelta

    import taggle_rx.store as store_module
    from taggle_rx.store import Store

    from .test_guided_calibration import ID, START, radio

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return (START + timedelta(days=3)).astimezone(tz)

    monkeypatch.setattr(store_module, 'datetime', Clock)
    broker = Broker()
    cfg = Config.from_dict({'meter_ids': [ID], 'data_dir': str(tmp_path),
                            'mqtt': {'host': '127.0.0.1', 'port': broker.port}})
    publisher = Publisher(cfg)
    store = Store(cfg, publisher)
    store.refresh(Clock.now())
    radio(store, 0, (100, 100, 100))
    radio(store, 1, (200, 100, 100))
    try:
        publisher.start()
        broker.wait(lambda rows: ('taggle/status', 'online') in rows)

        def command(action, payload, predicate):
            before = len(broker.records)
            broker.send(f'taggle/{ID}/{action}/set', payload)
            broker.wait(lambda rows: any(topic == f'taggle/{ID}/state' and predicate(json.loads(value))
                                         for topic, value in rows[before:]))

        expected = {f'taggle/{ID}/{a}/set' for a in ('reading', 'reading_time', 'dial_unit', 'reset')}
        assert expected <= set(broker.subscriptions)
        command('dial_unit', 'L', lambda s: s['dial_unit'] == 'L')
        command('reading_time', START.isoformat(), lambda s: bool(s['reading_time']))
        command('reading', '100000', lambda s: s.get('enter_reading') == 100000 and s['reading_time'] == '')
        command('reading', json.dumps({'litres': 100500, 'time': (START + timedelta(hours=1)).isoformat(),
                                       'source': 'phone photo'}), lambda s: s.get('litres_per_count') == 5)
        broker.wait(lambda rows: any(topic.endswith('/meter_reading/config') and value for topic, value in rows))
        broker.wait(lambda rows: any(topic.endswith('/calibration') and json.loads(value).get('chosen_k') == 5
                                     for topic, value in rows))
        attrs = [json.loads(value) for topic, value in broker.records if topic.endswith('/calibration')][-1]
        assert attrs['chosen_k'] == 5
        assert attrs['readings'][1]['source'] == 'phone photo'
        assert attrs['next_transmission_expected'].startswith('Next transmission expected ≈ ')
        configs = {topic: json.loads(value) for topic, value in broker.records
                   if topic.endswith('/config') and value}
        number = configs['homeassistant/number/taggle_123456/enter_reading/config']
        assert number['mode'] == 'box' and number['step'] == .001 and not number['retain']
        assert number['default_entity_id'] == 'number.taggle_123456_enter_reading'
        assert number['name'] == 'Meter reading (from dial)'
        assert configs['homeassistant/select/taggle_123456/dial_unit/config']['name'] == 'Dial unit (m³ / kL / L)'
        assert configs['homeassistant/text/taggle_123456/reading_time/config']['name'] == 'Photo time (optional, HH:MM)'
        absolute = configs['homeassistant/sensor/taggle_123456/meter_reading/config']
        assert absolute['device_class'] == 'water' and absolute['state_class'] == 'total_increasing'
        assert absolute['suggested_display_precision'] == 0
        # A retained reset must never erase readings during reconnect.
        broker.send(f'taggle/{ID}/reset/set', 'RESET', retain=True)
        broker.source.shutdown(socket.SHUT_RDWR)
        broker.wait(lambda rows: broker.connections >= 2 and broker.subscriptions.count(f'taggle/{ID}/reading/set') >= 2)
        assert len(store.meters[str(ID)]['calibration']['readings']) == 2
        before = len(broker.records)
        broker.send('homeassistant/status', 'online')
        broker.wait(lambda rows: any(topic.endswith('/reading_time/config') for topic, _ in rows[before:]))
        command('reading', '{"delete":2}', lambda s: 'litres_per_count' not in s)
        command('reading', '{"litres":100500,"time":"2026-11-02T03:41+10:00"}',
                lambda s: s.get('litres_per_count') == 5)
        command('reset', 'RESET', lambda s: 'litres_per_count' not in s)
        assert not store.meters[str(ID)]['calibration']['readings']
        broker.wait(lambda rows: rows[-1:] and any(topic.endswith('/meter_reading/config') and value == ''
                                                   for topic, value in rows[before:]))
    finally:
        publisher.close()
        broker.close()
