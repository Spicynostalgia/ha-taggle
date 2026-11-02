"""Retained Home Assistant discovery with availability and reconnect support."""
import json
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from . import __version__

# key: (display name, unit, device class, state class)
ENTITIES = {
    'last_hour': ('Water last hour', 'pulses', None, 'measurement'),
    'today': ('Water today', 'pulses', None, None),
    'meter_count': ('Meter count', 'pulses', None, 'total_increasing'),
    'snr': ('SNR', 'dB', 'signal_strength', 'measurement'),
    'signal_level': ('Signal level', 'dBFS', None, 'measurement'),
    'last_seen': ('Last seen', None, 'timestamp', None),
    'last_hour_litres': ('Water last hour litres', 'L', 'water', None),
    'today_litres': ('Water today litres', 'L', 'water', None),
    'total_litres': ('Water total litres', 'L', 'water', 'total_increasing'),
    'vs_neighbourhood_today': ('Vs neighbourhood today', '%', None, 'measurement'),
}
DIAGNOSTICS = {'snr', 'signal_level', 'last_seen'}
NEIGHBOURHOOD_ENTITIES = {
    'meters_heard': 'Meters heard',
    'meters_counted': 'Meters counted',
    'average_today': 'Average today',
    'median_today': 'Median today',
    'average_last_hour': 'Average last hour',
}


class Publisher:
    def __init__(self, config, client=None):
        self.config = config
        self.prefix = config.mqtt['topic_prefix']
        self.discovery_prefix = config.mqtt['discovery_prefix']
        self.latest = {}
        self.latest_neighbourhood = None
        self.lock = threading.RLock()
        self.client = client or mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                            client_id=f'{self.prefix.replace("/", "_")}_receiver')
        self.client.max_queued_messages_set(128)
        self.client.reconnect_delay_set(1, 60)
        self.client.will_set(f'{self.prefix}/status', 'offline', qos=1, retain=True)
        if config.mqtt['username']:
            self.client.username_pw_set(config.mqtt['username'], config.mqtt['password'])
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.connect_async(self.config.mqtt['host'], self.config.mqtt['port'], 60)
        self.client.loop_start()

    def send(self, topic, value):
        payload = value if isinstance(value, str) else json.dumps(value, allow_nan=False)
        return self.client.publish(topic, payload, qos=1, retain=True)

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            return
        client.subscribe(f'{self.discovery_prefix}/status', qos=1)
        self.announce()

    def on_message(self, client, userdata, message):
        if message.topic == f'{self.discovery_prefix}/status' and message.payload == b'online':
            self.announce()

    def announce(self):
        with self.lock:
            for identifier in self.config.meter_ids:
                for key, spec in ENTITIES.items():
                    topic = f'{self.discovery_prefix}/sensor/{self.prefix.replace("/", "_")}_{identifier}/{key}/config'
                    if (key.endswith('_litres') and identifier not in self.config.litres_per_count
                            or key == 'vs_neighbourhood_today' and not self.config.neighbourhood):
                        # Remove stale calibration discovery after configuration changes.
                        self.send(topic, '')
                        continue
                    self.send(topic, self.discovery(identifier, key, spec))
            for key in NEIGHBOURHOOD_ENTITIES:
                topic = (f'{self.discovery_prefix}/sensor/'
                         f'{self.prefix.replace("/", "_")}_neighbourhood/{key}/config')
                self.send(topic, self.neighbourhood_discovery(key) if self.config.neighbourhood else '')
            if self.config.neighbourhood:
                self.send(f'{self.prefix}/neighbourhood/state', self.latest_neighbourhood or
                          dict.fromkeys(NEIGHBOURHOOD_ENTITIES))
            else:
                # Remove retained aggregate data when the feature is disabled.
                self.send(f'{self.prefix}/neighbourhood/state', '')
            for identifier, state in self.latest.items():
                self._publish(identifier, state)
            self.send(f'{self.prefix}/status', 'online')

    def discovery(self, identifier, key, spec):
        name, unit, device_class, state_class = spec
        base = f'{self.prefix}/{identifier}'
        result = {
            'name': name, 'unique_id': f'{self.prefix}_{identifier}_{key}',
            'object_id': f'taggle_{identifier}_{key}', 'state_topic': f'{base}/state',
            'value_template': '{{ value_json.' + key + ' | default(none) }}',
            'availability_mode': 'all',
            'availability': [{'topic': f'{self.prefix}/status'},
                             {'topic': f'{base}/available' if key in DIAGNOSTICS else f'{base}/counts_available'}],
            'device': {'identifiers': [f'{self.prefix}_{identifier}'],
                       'name': f'Taggle {identifier}', 'manufacturer': 'Taggle Systems',
                       'model': 'Water meter transmitter', 'sw_version': __version__},
        }
        if key in DIAGNOSTICS:
            result['entity_category'] = 'diagnostic'
        if unit:
            result['unit_of_measurement'] = unit
        if device_class:
            result['device_class'] = device_class
        if state_class:
            result['state_class'] = state_class
        if key in ('last_hour', 'last_hour_litres'):
            result['json_attributes_topic'] = f'{base}/attributes'
        return result

    def neighbourhood_discovery(self, key):
        result = {
            'name': NEIGHBOURHOOD_ENTITIES[key],
            'unique_id': f'{self.prefix}_neighbourhood_{key}',
            'object_id': f'taggle_neighbourhood_{key}',
            'state_topic': f'{self.prefix}/neighbourhood/state',
            'value_template': '{{ value_json.' + key + ' | default(none) }}',
            'availability_topic': f'{self.prefix}/status',
            'state_class': 'measurement',
            'unit_of_measurement': ('meters' if key.startswith('meters_') else
                                    'L' if self.config.neighbourhood_factor is not None else 'pulses'),
            'device': {'identifiers': [f'{self.prefix}_neighbourhood'],
                       'name': 'Taggle neighbourhood', 'manufacturer': 'Taggle Systems',
                       'model': 'Anonymous receiver aggregate', 'sw_version': __version__},
        }
        return result

    def publish_neighbourhood(self, state):
        if not self.config.neighbourhood:
            return
        # Whitelist the aggregate surface; opaque neighbour keys stay in the store.
        with self.lock:
            self.latest_neighbourhood = {key: state.get(key) for key in NEIGHBOURHOOD_ENTITIES}
            if self.client.is_connected():
                self.send(f'{self.prefix}/neighbourhood/state', self.latest_neighbourhood)

    def publish(self, identifier, state):
        with self.lock:
            self.latest[identifier] = state
            if self.client.is_connected():
                self._publish(identifier, state)

    def _publish(self, identifier, state):
        base = f'{self.prefix}/{identifier}'
        recent = (datetime.now(timezone.utc) - datetime.fromisoformat(state['last_seen'])).total_seconds() < 3 * 3600
        self.send(f'{base}/available', 'online' if recent else 'offline')
        self.send(f'{base}/counts_available', 'online' if recent and 'meter_count' in state else 'offline')
        self.send(f'{base}/state', {k: v for k, v in state.items() if k != 'history'})
        self.send(f'{base}/attributes', {k: state[k] for k in (
            'history', 'hours_observed', 'litres_per_count', 'encrypted', 'raw_count') if k in state})

    def close(self):
        if self.client.is_connected():
            self.send(f'{self.prefix}/status', 'offline').wait_for_publish(timeout=3)
        self.client.disconnect()
        self.client.loop_stop()
