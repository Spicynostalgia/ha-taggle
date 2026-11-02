"""Validated configuration, shared by CLI, Docker and the add-on."""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo


def meter_id(value):
    if isinstance(value, bool) or not str(value).isdecimal():
        raise ValueError('meter IDs must be decimal integers')
    result = int(value)
    if not 0 <= result < 2**20:
        raise ValueError('meter IDs must fit the 20-bit header')
    return result


@dataclass
class Config:
    meter_ids: list[int] = field(default_factory=list)
    log_all_meters: bool = False
    frequency: int = 922_200_000
    sample_rate: int = 2_400_000
    gain: float = 40.0
    device: str = '0'
    timezone: str = 'UTC'
    litres_per_count: dict = field(default_factory=dict)
    mqtt: dict = field(default_factory=dict)
    data_dir: str = './data'
    jsonl_logging: bool = False

    @classmethod
    def load(cls, path, *, scan=False):
        return cls.from_dict(json.loads(Path(path).read_text()), scan=scan)

    @classmethod
    def from_dict(cls, raw, *, scan=False):
        config = cls(**raw)
        for name in ('log_all_meters', 'jsonl_logging'):
            if not isinstance(getattr(config, name), bool):
                raise ValueError(f'{name} must be boolean')
        if not isinstance(config.meter_ids, list):
            raise ValueError('meter_ids must be a list')
        config.meter_ids = sorted({meter_id(v) for v in config.meter_ids})
        if not config.meter_ids and not config.log_all_meters and not scan:
            raise ValueError('configure meter_ids or explicitly enable log_all_meters')
        if config.sample_rate != 2_400_000:
            raise ValueError('only 2400000 samples/s is supported')
        if not isinstance(config.frequency, int) or not 921_700_000 <= config.frequency <= 922_490_000:
            raise ValueError('frequency must keep the supported channel inside the sampled band')
        if isinstance(config.gain, bool) or not math.isfinite(config.gain) or not 0 <= config.gain <= 50:
            raise ValueError('gain must be between 0 and 50 dB')
        config.device = str(config.device)
        if not config.device or config.device.startswith('-'):
            raise ValueError('invalid RTL device index/serial')
        ZoneInfo(config.timezone)
        scales = config.litres_per_count
        if isinstance(scales, list):
            scales = {item['meter_id']: item['value'] for item in scales}
        if not isinstance(scales, dict):
            raise ValueError('litres_per_count must be a mapping or list')
        config.litres_per_count = {}
        for key, value in scales.items():
            key = meter_id(key)
            if key not in config.meter_ids:
                raise ValueError('calibration requires a configured meter')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('litres_per_count must be finite and positive')
            config.litres_per_count[key] = float(value)
        defaults = dict(host='localhost', port=1883, username='', password='',
                        topic_prefix='taggle', discovery_prefix='homeassistant')
        if not isinstance(config.mqtt, dict) or set(config.mqtt) - set(defaults):
            raise ValueError('unknown MQTT option')
        config.mqtt = {**defaults, **config.mqtt}
        if not isinstance(config.mqtt['port'], int) or not 1 <= config.mqtt['port'] <= 65535:
            raise ValueError('invalid MQTT port')
        for name in ('topic_prefix', 'discovery_prefix'):
            prefix = config.mqtt[name]
            if not isinstance(prefix, str) or not prefix or any(c in prefix for c in '+#\x00'):
                raise ValueError('MQTT prefixes must be nonempty and contain no wildcards')
            config.mqtt[name] = prefix.rstrip('/')
            if not config.mqtt[name]:
                raise ValueError('empty MQTT prefix')
        return config

    def allows(self, identifier):
        return identifier in self.meter_ids or self.log_all_meters
