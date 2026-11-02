"""Validated configuration, shared by CLI, Docker and the add-on."""
import json
import logging
import math
from dataclasses import dataclass, field, fields
from pathlib import Path
from zoneinfo import ZoneInfo

from .leak import validate_options as validate_leak_options


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
    neighbourhood: bool = True
    neighbourhood_min_meters: int = 3
    neighbourhood_litres_per_count: float | None = None
    frequency: int = 922_200_000
    sample_rate: int = 2_400_000
    gain: float = 40.0
    device: str = '0'
    timezone: str = 'UTC'
    litres_per_count: dict = field(default_factory=dict)
    meter_reading_offset: dict = field(default_factory=dict)
    dial_unit: str = 'm3'
    calibration_max_uncertainty: float = .02
    mqtt: dict = field(default_factory=dict)
    data_dir: str = './data'
    jsonl_logging: bool = False
    leak_detection: bool = True
    leak_continuous_hours: int = 24
    leak_night_start: str = '01:00'
    leak_night_end: str = '05:00'
    leak_night_min_pulses: int = 1

    @classmethod
    def load(cls, path, *, scan=False):
        return cls.from_dict(json.loads(Path(path).read_text()), scan=scan)

    @classmethod
    def from_dict(cls, raw, *, scan=False):
        if not isinstance(raw, dict):
            raise ValueError('configuration must be an object')
        known = {f.name for f in fields(cls)}
        for name in raw.keys() - known:
            logging.getLogger(__name__).warning('Ignoring unknown option %s', name)
        config = cls(**{k: v for k, v in raw.items() if k in known})
        for name in ('log_all_meters', 'jsonl_logging', 'neighbourhood'):
            if not isinstance(getattr(config, name), bool):
                raise ValueError(f'{name} must be boolean')
        if not isinstance(config.meter_ids, list):
            raise ValueError('meter_ids must be a list')
        config.meter_ids = list(dict.fromkeys(meter_id(v) for v in config.meter_ids))
        floor = config.neighbourhood_min_meters
        if isinstance(floor, bool) or not isinstance(floor, int):
            raise ValueError('neighbourhood_min_meters must be an integer')
        config.neighbourhood_min_meters = max(3, floor)
        factor = config.neighbourhood_litres_per_count
        if factor is not None and (isinstance(factor, bool) or not isinstance(factor, (int, float))
                                   or not math.isfinite(factor) or factor <= 0):
            raise ValueError('neighbourhood_litres_per_count must be finite and positive')
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
        validate_leak_options(config)
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
        if config.dial_unit not in ('m3', 'kl', 'litres', 'm³', 'kL', 'L'):
            raise ValueError('dial_unit must be m3, kl or L')
        value = config.calibration_max_uncertainty
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 0 < value <= 1):
            raise ValueError('calibration_max_uncertainty must be finite, positive and at most 1')
        offsets = config.meter_reading_offset
        if isinstance(offsets, list):
            offsets = {item['meter_id']: item['value'] for item in offsets}
        if not isinstance(offsets, dict):
            raise ValueError('meter_reading_offset must be a mapping or list')
        config.meter_reading_offset = {}
        for key, value in offsets.items():
            key = meter_id(key)
            if (key not in config.litres_per_count or isinstance(value, bool)
                    or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError('meter_reading_offset requires a pinned factor and a finite offset')
            config.meter_reading_offset[key] = float(value)
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

    @property
    def neighbourhood_factor(self):
        if self.neighbourhood_litres_per_count is not None:
            return self.neighbourhood_litres_per_count
        return self.litres_per_count.get(self.meter_ids[0]) if self.meter_ids else None
