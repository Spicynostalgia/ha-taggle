"""Possible-leak hints from observed hourly intervals, never estimated flow.

Evaluation is pure: callers may checkpoint the returned rule state to retain a
hint across reception gaps/restarts. Missing intervals neither trigger nor clear
it. Local wall times select night intervals; UTC orders elapsed hours across DST.
"""
import re
from datetime import datetime, time, timedelta, timezone

ATTRIBUTES = ('reason', 'hours_with_flow_last_24h', 'longest_zero_run_hours',
              'night_pulses', 'observed_hours', 'last_evaluated')


def parse_clock(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise ValueError('night window times must use HH:MM (00:00–23:59)')
    return time.fromisoformat(value)


def validate_options(config):
    if not isinstance(config.leak_detection, bool):
        raise ValueError('leak_detection must be boolean')
    for name, maximum in (('leak_continuous_hours', 168), ('leak_night_min_pulses', 65535)):
        value = getattr(config, name)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError(f'{name} must be an integer between 1 and {maximum}')
    if parse_clock(config.leak_night_start) == parse_clock(config.leak_night_end):
        raise ValueError('night window start and end must differ')


def continuous_flow(rows, required, previous=False, last_end=None):
    """Latch on sufficient positive coverage; only a new observed zero clears."""
    active = previous
    for index, (end, pulses) in enumerate(rows):
        if last_end is not None and end <= last_end:
            continue
        if pulses == 0:
            active = False
        else:
            window = [p for stamp, p in rows[:index + 1] if end - timedelta(hours=required) < stamp]
            if len(window) >= required * .8 and all(p > 0 for p in window):
                active = True
    return active


def night_flow(rows, now, zone, start, end, minimum, active=None, checked=None):
    """Decide completed nights with at least three observations; otherwise retain state."""
    nights = {}
    for stamp, pulses in rows:
        local = stamp.astimezone(zone)
        clock = local.time()
        inside = start <= clock < end if start < end else clock >= start or clock < end
        if inside:
            day = local.date() - timedelta(days=int(start > end and clock < end))
            nights.setdefault(day.isoformat(), []).append((stamp, pulses))
    latest_pulses = sum(p for _, p in next(reversed(nights.values()))) if nights else 0
    local_now = now.astimezone(zone)
    for day, intervals in nights.items():
        if checked is not None and day < checked:
            continue
        end_day = datetime.fromisoformat(day).date() + timedelta(days=int(start > end))
        # End at the later occurrence of an ambiguous clock time. The wall-time
        # check also keeps a nonexistent spring-forward end open until the jump.
        end_utc = datetime.combine(end_day, end, zone).replace(fold=1).astimezone(timezone.utc)
        complete = (local_now.date() > end_day or
                    local_now.date() == end_day and local_now.time() >= end)
        if complete and now >= end_utc and len(intervals) >= 3:
            active = day if all(p >= minimum for _, p in intervals) else None
            checked = day
    return active, checked, latest_pulses


def evaluate(history, now, config, zone, previous=None):
    """Return wire attributes and checkpointable latches without mutating inputs."""
    now = now.astimezone(timezone.utc)
    settings = [config.timezone, config.leak_continuous_hours, config.leak_night_start,
                config.leak_night_end, config.leak_night_min_pulses]
    previous = previous or {}
    if previous.get('_settings') != settings:
        previous = {}
    rows = sorted((datetime.fromisoformat(h['end']).astimezone(timezone.utc), h['counts'])
                  for h in history.values() if datetime.fromisoformat(h['end']) <= now)
    last_end = datetime.fromisoformat(previous['_last_end']) if previous.get('_last_end') else None
    continuous = continuous_flow(rows, config.leak_continuous_hours,
                                 previous.get('_continuous', False), last_end)
    night, checked, pulses = night_flow(rows, now, zone, parse_clock(config.leak_night_start),
                                       parse_clock(config.leak_night_end), config.leak_night_min_pulses,
                                       previous.get('_night'), previous.get('_night_checked'))
    recent = [(stamp, p) for stamp, p in rows if now - timedelta(hours=24) < stamp]
    identities = {datetime.fromisoformat(h['end']): int(key) for key, h in history.items()}
    longest = run = 0
    last = None
    for stamp, count in recent:
        # Stored hourly identities distinguish real gaps from timestamp drift.
        identity = identities[stamp]
        run = (run + 1 if last is not None and identity == last + 1 else 1) if count == 0 else 0
        longest = max(longest, run)
        last = identity
    reason = (f'continuous flow for {config.leak_continuous_hours} h' if continuous else
              'night flow' if night else None)
    return {
        'state': 'ON' if reason else 'OFF', 'reason': reason,
        'hours_with_flow_last_24h': sum(p > 0 for _, p in recent),
        'longest_zero_run_hours': longest, 'night_pulses': pulses,
        'observed_hours': len(recent), 'last_evaluated': now.isoformat(),
        '_continuous': continuous, '_night': night, '_night_checked': checked,
        '_last_end': rows[-1][0].isoformat() if rows else previous.get('_last_end'),
        '_settings': settings,
    }
