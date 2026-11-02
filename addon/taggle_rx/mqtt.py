"""Retained Home Assistant discovery with availability and reconnect support."""
import json
import logging
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from . import __version__

LOG = logging.getLogger(__name__)

# key: (display name, unit, device class, state class)
ENTITIES = {
    'last_hour': ('Last hour', 'pulses', None, 'measurement'),
    'today': ('Today', 'pulses', None, None),
    'meter_count': ('Meter count', 'pulses', None, 'total_increasing'),
    'snr': ('SNR', 'dB', 'signal_strength', 'measurement'),
    'signal_level': ('Signal level', 'dBFS', None, 'measurement'),
    'last_seen': ('Last seen', None, 'timestamp', None),
    'last_hour_litres': ('Last hour litres', 'L', 'water', None),
    'today_litres': ('Today litres', 'L', 'water', None),
    'total_litres': ('Total litres', 'L', 'water', 'total_increasing'),
    'meter_reading': ('Meter reading', 'L', 'water', 'total_increasing'),
    'calibration_status': ('Calibration status', None, None, None),
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


def state_value(value):
    """Limit wire precision without changing stored measurements or calculations."""
    return round(value, 2) if isinstance(value, float) else value


class Publisher:
    def __init__(self, config, client=None):
        self.config = config
        self.prefix = config.mqtt['topic_prefix']
        self.discovery_prefix = config.mqtt['discovery_prefix']
        self.latest = {}
        self.latest_neighbourhood = None
        self.lock = threading.RLock()
        self.command_handler = None
        self.discovery_signature = {}
        self.client = client or mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                            client_id=f'{self.prefix.replace("/", "_")}_receiver')
        self.client.max_queued_messages_set(128)
        self.client.reconnect_delay_set(1, 60)
        self.client.will_set(f'{self.prefix}/status', 'offline', qos=1, retain=True)
        if config.mqtt['username']:
            self.client.username_pw_set(config.mqtt['username'], config.mqtt['password'])
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
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
        LOG.info('MQTT connected to %s:%s', self.config.mqtt['host'], self.config.mqtt['port'])
        client.subscribe(f'{self.discovery_prefix}/status', qos=1)
        self.subscribe_commands(client)
        self.announce()

    def subscribe_commands(self, client):
        for identifier in self.config.meter_ids:
            for action in ('reading', 'dial_unit', 'reading_time', 'reset'):
                client.subscribe(f'{self.prefix}/{identifier}/{action}/set', qos=1)

    def on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties=None):
        LOG.info('MQTT disconnected from %s:%s', self.config.mqtt['host'], self.config.mqtt['port'])

    def on_message(self, client, userdata, message):
        if message.topic == f'{self.discovery_prefix}/status' and message.payload == b'online':
            self.subscribe_commands(client)
            self.announce()
            return
        # Retained commands would replay a dial entry/reset after every reconnect.
        if getattr(message, 'retain', False) is True or not self.command_handler:
            return
        for identifier in self.config.meter_ids:
            for action in ('reading', 'dial_unit', 'reading_time', 'reset'):
                if message.topic == f'{self.prefix}/{identifier}/{action}/set':
                    try:
                        if len(message.payload) > 4096:
                            raise ValueError('command too long')
                        payload = message.payload.decode('utf-8')
                    except (UnicodeError, ValueError):
                        LOG.info('Meter %s calibration: rejected invalid command encoding/length', identifier)
                        return
                    self.command_handler(identifier, action, payload)
                    return

    def factor(self, identifier):
        state = self.latest.get(identifier, {})
        return (state.get('calibration', {}).get('chosen_k') or
                state.get('litres_per_count', self.config.litres_per_count.get(identifier)))

    @property
    def neighbourhood_factor(self):
        if self.config.neighbourhood_litres_per_count is not None:
            return self.config.neighbourhood_litres_per_count
        if not self.config.meter_ids:
            return None
        first = self.config.meter_ids[0]
        return self.factor(first)

    def announce_meter(self, identifier):
        state = self.latest.get(identifier, {})
        factor = self.factor(identifier)
        for key, spec in ENTITIES.items():
            topic = f'{self.discovery_prefix}/sensor/{self.prefix.replace("/", "_")}_{identifier}/{key}/config'
            enabled = not ((key.endswith('_litres') and factor is None)
                           or (key == 'meter_reading' and 'meter_reading' not in state)
                           or (key == 'vs_neighbourhood_today' and not self.config.neighbourhood))
            self.send(topic, self.discovery(identifier, key, spec) if enabled else '')
        for key, domain in (('dial_unit', 'select'), ('enter_reading', 'number'),
                            ('reading_time', 'text'), ('reset_calibration', 'button')):
            topic = f'{self.discovery_prefix}/{domain}/{self.prefix.replace("/", "_")}_{identifier}/{key}/config'
            self.send(topic, self.control_discovery(identifier, key, domain))
        self.discovery_signature[identifier] = (factor, 'meter_reading' in state)

    def control_discovery(self, identifier, key, domain):
        names = {'dial_unit': 'Dial unit', 'enter_reading': 'Enter meter reading',
                 'reading_time': 'Reading time', 'reset_calibration': 'Reset calibration'}
        action = {'enter_reading': 'reading', 'reset_calibration': 'reset'}.get(key, key)
        result = self.discovery(identifier, key, (names[key], None, None, None))
        result['default_entity_id'] = f'{domain}.taggle_{identifier}_{key}'
        result['command_topic'] = f'{self.prefix}/{identifier}/{action}/set'
        result['retain'] = False
        if domain == 'select':
            result['options'] = ['m³', 'kL', 'L']
        elif domain == 'number':
            result.update(mode='box', min=0, max=1e15, step=.001)
        elif domain == 'text':
            result.update(mode='text', min=0, max=64)
        else:
            result.pop('state_topic')
            result.pop('value_template')
            result['payload_press'] = 'RESET'
        return result

    def announce(self):
        with self.lock:
            for identifier in self.config.meter_ids:
                self.announce_meter(identifier)
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
            'default_entity_id': f'sensor.taggle_{identifier}_{key}', 'state_topic': f'{base}/state',
            'value_template': '{{ value_json.' + key + ' | default(none) }}',
            'availability_mode': 'all',
            'availability': [{'topic': f'{self.prefix}/status'},
                             {'topic': f'{base}/available' if key in DIAGNOSTICS else f'{base}/counts_available'}],
            'device': {'identifiers': [f'{self.prefix}_{identifier}'],
                       'name': f'Taggle {identifier}', 'manufacturer': 'Taggle Systems',
                       'model': 'Water meter transmitter', 'sw_version': __version__},
        }
        if key in ('calibration_status', 'dial_unit', 'enter_reading', 'reading_time', 'reset_calibration'):
            result.pop('availability_mode')
            result.pop('availability')
            result['availability_topic'] = f'{self.prefix}/status'
        if key == 'calibration_status':
            result['json_attributes_topic'] = f'{base}/calibration'
        if key in DIAGNOSTICS:
            result['entity_category'] = 'diagnostic'
        if unit:
            result['unit_of_measurement'] = unit
            result['suggested_display_precision'] = 0 if unit == 'pulses' or key == 'meter_reading' else 1
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
            'default_entity_id': f'sensor.taggle_neighbourhood_{key}',
            'state_topic': f'{self.prefix}/neighbourhood/state',
            'value_template': '{{ value_json.' + key + ' | default(none) }}',
            'availability_topic': f'{self.prefix}/status',
            'state_class': 'measurement',
            'unit_of_measurement': ('meters' if key.startswith('meters_') else
                                    'L' if self.neighbourhood_factor is not None else 'pulses'),
            'suggested_display_precision': (0 if key.startswith('meters_') or
                                             self.neighbourhood_factor is None else 1),
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
            self.latest_neighbourhood = {key: state_value(state.get(key)) for key in NEIGHBOURHOOD_ENTITIES}
            if self.client.is_connected():
                self.send(f'{self.prefix}/neighbourhood/state', self.latest_neighbourhood)

    def publish(self, identifier, state):
        with self.lock:
            previous_factor = self.neighbourhood_factor
            self.latest[identifier] = state
            if self.client.is_connected():
                factor = self.factor(identifier)
                if self.discovery_signature.get(identifier) != (factor, 'meter_reading' in state):
                    self.announce_meter(identifier)
                if previous_factor != self.neighbourhood_factor and self.config.neighbourhood:
                    for key in NEIGHBOURHOOD_ENTITIES:
                        topic = (f'{self.discovery_prefix}/sensor/'
                                 f'{self.prefix.replace("/", "_")}_neighbourhood/{key}/config')
                        self.send(topic, self.neighbourhood_discovery(key))
                self._publish(identifier, state)

    def _publish(self, identifier, state):
        base = f'{self.prefix}/{identifier}'
        recent = bool(state.get('last_seen')) and (datetime.now(timezone.utc) -
                  datetime.fromisoformat(state['last_seen'])).total_seconds() < 3 * 3600
        self.send(f'{base}/available', 'online' if recent else 'offline')
        self.send(f'{base}/counts_available', 'online' if recent and 'meter_count' in state else 'offline')
        self.send(f'{base}/state', {k: state_value(v) if k in ENTITIES else v
                                  for k, v in state.items() if k not in ('history', 'calibration')})
        self.send(f'{base}/calibration', state.get('calibration', {}))
        self.send(f'{base}/attributes', {k: state[k] for k in (
            'history', 'hours_observed', 'litres_per_count', 'encrypted', 'raw_count') if k in state})

    def close(self):
        if self.client.is_connected():
            self.send(f'{self.prefix}/status', 'offline').wait_for_publish(timeout=3)
        self.client.disconnect()
        self.client.loop_stop()
