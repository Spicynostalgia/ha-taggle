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
