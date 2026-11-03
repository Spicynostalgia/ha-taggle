"""Private-by-default filtering and atomic, bounded usage checkpoints."""
import copy
import hashlib
import hmac
import json
import logging
import os
import re
import statistics
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from zoneinfo import ZoneInfo

from . import calibration
from .leak import evaluate as evaluate_leak

LOG = logging.getLogger(__name__)
HEARTBEAT_SECONDS = 15 * 60


def synchronized(method):
    @wraps(method)
    def locked(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)
    return locked


class Store:
    def __init__(self, config, publisher=None, scan=None):
        self.lock = threading.RLock()
        self.config = config
        self.publisher = publisher
        self.scan = scan
        self.zone = ZoneInfo(config.timezone)
        self.path = Path(config.data_dir)
        self.meters = {}
        self.read_window_deadlines = {}
        self.neighbours = {}
        self.salt = None
        self.heartbeat_at = time.monotonic()
        self.other_frames = 0
        self.other_meters = set()  # In-memory cardinality only; never logged or persisted.
        if scan is None:
            self.path.mkdir(mode=0o700, parents=True, exist_ok=True)
            checkpoint = self.path / 'state.json'
            checkpoint_changed = False
            if checkpoint.exists():
                state = json.loads(checkpoint.read_text())
                if state.get('version') not in (1, 2):
                    raise ValueError('unsupported state version')
                self.meters = {k: v for k, v in state['meters'].items()
                               if int(k) in config.meter_ids}
                checkpoint_changed = self.meters != state['meters'] or state['version'] == 1
                if config.neighbourhood:
                    self.neighbours = {k: v for k, v in state.get('neighbours', {}).items()
                                       if re.fullmatch('[0-9a-f]{16}', k)}
                    checkpoint_changed |= self.neighbours != state.get('neighbours', {})
            salt_path = self.path / 'neighbourhood.salt'
            if config.neighbourhood:
                try:
                    fd = os.open(salt_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                except FileExistsError:
                    pass
                else:
                    with os.fdopen(fd, 'wb') as target:
                        target.write(os.urandom(32))
                        target.flush()
                        os.fsync(target.fileno())
                    # A missing salt cannot recover old opaque identities.
                    checkpoint_changed |= bool(self.neighbours)
                    self.neighbours = {}
                salt_path.chmod(0o600)
                self.salt = salt_path.read_bytes()
                if len(self.salt) != 32:
                    raise ValueError('invalid neighbourhood salt length')
                excluded = {self.neighbour_key(identifier) for identifier in config.meter_ids}
                removed = bool(excluded.intersection(self.neighbours))
                self.neighbours = {k: v for k, v in self.neighbours.items() if k not in excluded}
                if self.prune(datetime.now(timezone.utc)) or removed or checkpoint_changed:
                    self.save()
            else:
                salt_path.unlink(missing_ok=True)
                if checkpoint.exists():
                    self.save()

        if scan is None:
            for key, meter in self.meters.items():
                if 'calibration' not in meter:
                    meter['calibration'] = calibration.migrate(meter, config.dial_unit)
                cal = meter['calibration']
                if 'reading_time' in cal:
                    cal.pop('reading_time')
                    checkpoint_changed = True
                calibration.solve(cal, config, int(key), zone=self.zone)
            if publisher:
                publisher.command_handler = self.command
            if checkpoint_changed:
                self.save()

    def factor(self, identifier):
        meter = self.meters.get(str(identifier), {})
        solution = meter.get('calibration', {}).get('solution') or {}
        return self.config.litres_per_count.get(identifier, solution.get('factor'))

    @property
    def neighbourhood_factor(self):
        explicit = self.config.neighbourhood_litres_per_count
        return explicit if explicit is not None else self.factor(self.config.meter_ids[0]) if self.config.meter_ids else None

    @synchronized
    def command(self, identifier, action, payload, now=None):
        if identifier not in self.config.meter_ids or self.scan is not None:
            return
        now = now or datetime.now(timezone.utc)
        meter = self.meters.setdefault(str(identifier), {'hours': {}, 'meter_count': 0, 'total_litres': 0.0})
        cal = meter.setdefault('calibration', calibration.initial(self.config.dial_unit))
        try:
            if action == 'dial_unit':
                if payload not in ('m³', 'kL', 'L'):
                    raise ValueError('Choose m³, kL or L for Dial unit')
                cal['dial_unit'] = payload
                result = 'unit changed'
            elif action in ('reading', 'reset'):
                result = calibration.intake(cal, '{"reset":true}' if action == 'reset' else payload, now, self.zone)
            else:
                return
            cal.pop('error', None)
            calibration.solve(cal, self.config, identifier, now, self.zone)
            if result == 'accepted':
                last = cal['readings'][-1]
                result += (', pending' if not last.get('base_interval') else
                           ', rejected (stored, excluded)' if not last['used'] else
                           ', solved' if cal.get('solution') else '')
            LOG.info('Meter %s calibration: %s; %s', identifier, result, cal['status'])
        except (ValueError, TypeError, OverflowError) as error:
            cal['error'] = f'Check your reading: {error}'
            cal['status'] = cal['error']
            LOG.info('Meter %s calibration: rejected; %s', identifier, error)
        self.save()
        if self.publisher:
            self._publish_meter(identifier, now)

    @synchronized
    def save(self):
        fd, temporary = tempfile.mkstemp(dir=self.path, prefix='.state-')
        try:
            with os.fdopen(fd, 'w') as target:
                state = {'version': 2, 'meters': self.meters}
                if self.config.neighbourhood:
                    state['neighbours'] = self.neighbours
                json.dump(state, target, allow_nan=False)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, self.path / 'state.json')
            directory = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @synchronized
    def frame(self, frame, stamp):
        identifier = frame['meter_id']
        configured = identifier in self.config.meter_ids
        stamp = stamp.astimezone(timezone.utc)
        if self.scan is not None:
            row = {'time': stamp.isoformat(), 'meter_id': identifier,
                   'snr_median_db': round(frame['snr_median_db'], 1),
                   'signal_level_dbfs': round(frame['signal_level_dbfs'], 1)}
            if configured and 'counts' in frame:
                row['counts'] = frame['counts']
            self.scan(row)
            return
        if configured:
            if 'counts' in frame:
                delta = (frame['counts'][0] - frame['counts'][1]) % 65536
                LOG.info('Meter %s: +%d pulses last hour, SNR %.1f dB',
                         identifier, delta, frame['snr_median_db'])
            else:
                LOG.info('Meter %s: counts unavailable, SNR %.1f dB', identifier, frame['snr_median_db'])
        else:
            self.other_frames += 1
            self.other_meters.add(identifier)
        if not configured and self.config.neighbourhood:
            self.neighbour_frame(frame, stamp)
        if self.config.jsonl_logging and self.config.allows(identifier):
            # Never log raw bits, frame bytes or encrypted bodies.
            row = {k: v for k, v in frame.items() if k in (
                'meter_id', 'format_bytes', 'encrypted', 'sequence', 'counts', 'flags',
                'snr_median_db', 'signal_level_dbfs', 'fec_errors')}
            row['time'] = stamp.isoformat()
            fd = os.open(self.path / f'{stamp.date()}.jsonl', os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, 'a') as target:
                os.fchmod(target.fileno(), 0o600)
                target.write(json.dumps(row, allow_nan=False) + '\n')
        if not configured:
            return
        key = str(identifier)
        meter = self.meters.setdefault(key, {'hours': {}, 'meter_count': 0, 'total_litres': 0.0})
        if meter.get('last_seen') and stamp < datetime.fromisoformat(meter['last_seen']):
            return
        meter.update(last_seen=stamp.isoformat(), snr=frame['snr_median_db'],
                     signal_level=frame['signal_level_dbfs'], encrypted=frame['encrypted'])
        cal = meter.setdefault('calibration', calibration.initial(self.config.dial_unit))
        cal['last_frame'] = stamp.isoformat()
        if 'counts' in frame:
            self.counts(meter, frame, stamp, self.factor(identifier) or 0)
            before = cal['status']
            calibration.solve(cal, self.config, identifier, stamp, self.zone)
            if before != cal['status'] and cal['readings']:
                outcome = 'solved' if cal.get('solution') else 'pending'
                LOG.info('Meter %s calibration: %s; %s', identifier, outcome, cal['status'])
        else:
            # Opaque frames expose diagnostics only, even after a clear-format frame.
            meter.pop('latest', None)
        # Possible-leak rule state is private to configured meters.
        if self.config.leak_detection and not meter['encrypted'] and 'latest' in meter:
            meter['leak'] = evaluate_leak(meter['hours'], stamp, self.config, self.zone, meter.get('leak'))
        self.save()
        if self.publisher:
            self._publish_meter(identifier, stamp)

    def _publish_meter(self, identifier, now, neighbourhood=None):
        """Build the complete meter state for every publish path, while locked."""
        state = self.snapshot(identifier, now)
        if self.config.neighbourhood:
            if neighbourhood is None:
                neighbourhood = self.neighbourhood_snapshot(now)
            state['vs_neighbourhood_today'] = self.comparison(identifier, state, neighbourhood)
        self.publisher.publish(identifier, state)

    def counts(self, meter, frame, stamp, factor=0):
        previous = meter.get('latest')
        seq = frame['sequence']
        if previous:
            elapsed = (stamp - datetime.fromisoformat(previous['time'])).total_seconds() / 3600
            difference = (seq - previous['sequence']) % 256
            advance = difference + 256 * round((elapsed - difference) / 256)
            # A backwards/reset sequence is ambiguous: wait for a consistent baseline.
            if advance < 0 or abs(advance - elapsed) > 0.5:
                meter.pop('latest', None)
                if 'calibration' in meter:
                    meter['calibration']['blocked'] = True
                return
            index = previous['index'] + advance
        else:
            index = round(stamp.timestamp() / 3600)
        if 'calibration' in meter:
            calibration.slots(meter['calibration'], frame, stamp, index)
        for age in (0, 1):
            identity = str(index - age)
            if identity in meter['hours']:
                continue
            end = stamp - timedelta(hours=age)
            delta = (frame['counts'][age] - frame['counts'][age + 1]) % 65536
            meter['hours'][identity] = {'end': end.isoformat(), 'counts': delta}
            meter['meter_count'] += delta
            meter['total_litres'] += delta * factor
        meter['latest'] = {'sequence': seq, 'index': index, 'time': stamp.isoformat(),
                           'raw_count': frame['counts'][0]}
        cutoff = stamp - timedelta(days=8)
        meter['hours'] = {k: v for k, v in meter['hours'].items()
                          if datetime.fromisoformat(v['end']) >= cutoff}

    @synchronized
    def snapshot(self, identifier, now):
        meter = self.meters[str(identifier)]
        result = {k: meter[k] for k in ('last_seen', 'snr', 'signal_level', 'encrypted') if k in meter}
        cal = meter.get('calibration', calibration.initial(self.config.dial_unit))
        calibration.solve(cal, self.config, identifier, now, self.zone)
        attrs = calibration.attributes(cal, now, self.zone)
        window = attrs['read_dial_now']
        if window['state'] == 'ON':
            self.read_window_deadlines[identifier] = datetime.fromisoformat(window['until'])
        else:
            self.read_window_deadlines.pop(identifier, None)
        result.update(calibration_status=cal['status'], calibration=copy.deepcopy(attrs), dial_unit=cal['dial_unit'],
                      dial_reading=cal.get('last_entry', ''), read_dial_now=attrs['read_dial_now'])
        if meter.get('encrypted') or 'latest' not in meter:
            return result
        hours = sorted(meter['hours'].values(), key=lambda v: v['end'])
        today = [h for h in hours if datetime.fromisoformat(h['end']).astimezone(self.zone).date()
                 == now.astimezone(self.zone).date()]
        result.update(last_hour=hours[-1]['counts'], today=sum(h['counts'] for h in today),
                      hours_observed=len(today), meter_count=meter['meter_count'],
                      raw_count=meter['latest']['raw_count'],
                      history=[h for h in hours if datetime.fromisoformat(h['end']) >= now - timedelta(hours=48)])
        factor = self.factor(identifier)
        if factor is not None:
            result.update(last_hour_litres=result['last_hour'] * factor,
                          today_litres=result['today'] * factor,
                          total_litres=meter['total_litres'], litres_per_count=factor)
        solution = cal.get('solution')
        if solution and solution['offset'] is not None and cal['slots'] and not cal.get('unresolved_gap'):
            edge = max(map(int, cal['slots']))
            count = cal['slots'][str(edge)]['count']
            count += 65536 * sum(int(w) for g, w in solution.get('wraps', {}).items() if int(g) <= edge)
            result['meter_reading'] = solution['offset'] + factor * count
        if self.config.leak_detection:
            result['possible_leak'] = evaluate_leak(meter['hours'], now, self.config, self.zone, meter.get('leak'))
        return result

    def neighbour_key(self, identifier):
        return hmac.new(self.salt, str(identifier).encode('ascii'), hashlib.sha256).hexdigest()[:16]

    def prune(self, now):
        cutoff = now - timedelta(days=7)
        expired = [key for key, meter in self.neighbours.items()
                   if datetime.fromisoformat(meter['last_seen']) < cutoff]
        for key in expired:
            del self.neighbours[key]
        return bool(expired)

    def neighbour_frame(self, frame, stamp):
        key = self.neighbour_key(frame['meter_id'])
        meter = self.neighbours.setdefault(key, {'hours': {}, 'meter_count': 0, 'total_litres': 0.0})
        if meter.get('last_seen') and stamp < datetime.fromisoformat(meter['last_seen']):
            return
        meter.update(last_seen=stamp.isoformat(), encrypted=frame['encrypted'])
        if not frame['encrypted'] and 'counts' in frame:
            # The shared delta routine receives no neighbour identifier.
            self.counts(meter, {'sequence': frame['sequence'], 'counts': frame['counts']}, stamp)
        else:
            meter.pop('latest', None)
        self.prune(stamp)
        self.save()

    def neighbourhood_snapshot(self, now):
        floor = max(3, self.config.neighbourhood_min_meters)
        local = now.astimezone(self.zone)
        elapsed = local.hour + local.minute / 60 + local.second / 3600
        heard, totals, recent = 0, [], []
        for meter in self.neighbours.values():
            if now - timedelta(hours=24) <= datetime.fromisoformat(meter['last_seen']) <= now:
                heard += 1
            if meter['encrypted'] or 'latest' not in meter:
                continue
            hours = [h for h in meter['hours'].values() if datetime.fromisoformat(h['end']) <= now]
            today = [h for h in hours if datetime.fromisoformat(h['end']).astimezone(self.zone).date()
                     == local.date()]
            if len(today) >= 6 and len(today) >= elapsed * .75:
                totals.append(sum(h['counts'] for h in today))
            if hours:
                last = max(hours, key=lambda h: h['end'])
                if datetime.fromisoformat(last['end']) >= now - timedelta(hours=2):
                    recent.append(last['counts'])
        factor = self.neighbourhood_factor
        scale = factor if factor is not None else 1
        return {
            'meters_heard': heard if heard >= floor else None,
            'meters_counted': len(totals) if len(totals) >= floor else None,
            'average_today': statistics.mean(totals) * scale if len(totals) >= floor else None,
            'median_today': statistics.median(totals) * scale if len(totals) >= floor else None,
            'average_last_hour': statistics.mean(recent) * scale if len(recent) >= floor else None,
        }

    @synchronized
    def expire_read_windows(self, now):
        """Publish OFF at the ten-minute deadline, independently of minute refreshes."""
        for identifier, deadline in list(self.read_window_deadlines.items()):
            if now >= deadline:
                self.read_window_deadlines.pop(identifier)
                if self.publisher:
                    self._publish_meter(identifier, now)

    @synchronized
    def refresh(self, now):
        """Republish date-dependent totals without changing the radio last-seen time."""
        neighbourhood = None
        if self.config.neighbourhood:
            if self.prune(now):
                self.save()
            neighbourhood = self.neighbourhood_snapshot(now)
        if self.publisher:
            for identifier in self.config.meter_ids:
                if str(identifier) not in self.meters:
                    cal = calibration.initial(self.config.dial_unit)
                    calibration.solve(cal, self.config, identifier, now, self.zone)
                    self.meters[str(identifier)] = {'hours': {}, 'meter_count': 0, 'total_litres': 0.0,
                                                    'calibration': cal}
            if neighbourhood is not None:
                self.publisher.publish_neighbourhood(neighbourhood)
            for key in self.meters:
                self._publish_meter(int(key), now, neighbourhood)

    def heartbeat(self):
        """Report reception during silence, with only counts for other meters."""
        now = time.monotonic()
        if self.scan is not None or now - self.heartbeat_at < HEARTBEAT_SECONDS:
            return
        LOG.info('still listening: %d frames from %d other meters heard in the last 15 min',
                 self.other_frames, len(self.other_meters))
        self.other_frames = 0
        self.other_meters.clear()
        self.heartbeat_at = now

    def comparison(self, identifier, state, neighbourhood):
        average = neighbourhood['average_today']
        if not average or 'today' not in state:
            return None
        if self.neighbourhood_factor is None:
            today = state['today']
        elif 'today_litres' in state:
            today = state['today_litres']
        else:
            return None
        return today / average * 100
