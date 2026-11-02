"""Private-by-default filtering and atomic, bounded usage checkpoints."""
import hashlib
import hmac
import json
import logging
import os
import re
import statistics
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .leak import evaluate as evaluate_leak

LOG = logging.getLogger(__name__)
HEARTBEAT_SECONDS = 15 * 60


class Store:
    def __init__(self, config, publisher=None, scan=None):
        self.config = config
        self.publisher = publisher
        self.scan = scan
        self.zone = ZoneInfo(config.timezone)
        self.path = Path(config.data_dir)
        self.meters = {}
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
                if state.get('version') != 1:
                    raise ValueError('unsupported state version')
                self.meters = {k: v for k, v in state['meters'].items()
                               if int(k) in config.meter_ids}
                checkpoint_changed = self.meters != state['meters']
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

    def save(self):
        fd, temporary = tempfile.mkstemp(dir=self.path, prefix='.state-')
        try:
            with os.fdopen(fd, 'w') as target:
                state = {'version': 1, 'meters': self.meters}
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
        if 'counts' in frame:
            self.counts(meter, frame, stamp, self.config.litres_per_count.get(identifier, 0))
        else:
            # Opaque frames expose diagnostics only, even after a clear-format frame.
            meter.pop('latest', None)
        # Possible-leak rule state is private to configured meters.
        if self.config.leak_detection and not meter['encrypted'] and 'latest' in meter:
            meter['leak'] = evaluate_leak(meter['hours'], stamp, self.config, self.zone, meter.get('leak'))
        self.save()
        if self.publisher:
            state = self.snapshot(identifier, stamp)
            if self.config.neighbourhood:
                state['vs_neighbourhood_today'] = self.comparison(
                    identifier, state, self.neighbourhood_snapshot(stamp))
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
                return
            index = previous['index'] + advance
        else:
            index = round(stamp.timestamp() / 3600)
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

    def snapshot(self, identifier, now):
        meter = self.meters[str(identifier)]
        result = {k: meter[k] for k in ('last_seen', 'snr', 'signal_level', 'encrypted')}
        if meter['encrypted'] or 'latest' not in meter:
            return result
        hours = sorted(meter['hours'].values(), key=lambda v: v['end'])
        today = [h for h in hours if datetime.fromisoformat(h['end']).astimezone(self.zone).date()
                 == now.astimezone(self.zone).date()]
        result.update(last_hour=hours[-1]['counts'], today=sum(h['counts'] for h in today),
                      hours_observed=len(today), meter_count=meter['meter_count'],
                      raw_count=meter['latest']['raw_count'],
                      history=[h for h in hours if datetime.fromisoformat(h['end']) >= now - timedelta(hours=48)])
        factor = self.config.litres_per_count.get(identifier)
        if factor is not None:
            result.update(last_hour_litres=result['last_hour'] * factor,
                          today_litres=result['today'] * factor,
                          total_litres=meter['total_litres'], litres_per_count=factor)
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
        factor = self.config.neighbourhood_factor
        scale = factor if factor is not None else 1
        return {
            'meters_heard': heard if heard >= floor else None,
            'meters_counted': len(totals) if len(totals) >= floor else None,
            'average_today': statistics.mean(totals) * scale if len(totals) >= floor else None,
            'median_today': statistics.median(totals) * scale if len(totals) >= floor else None,
            'average_last_hour': statistics.mean(recent) * scale if len(recent) >= floor else None,
        }

    def refresh(self, now):
        """Republish date-dependent totals without changing the radio last-seen time."""
        neighbourhood = None
        if self.config.neighbourhood:
            if self.prune(now):
                self.save()
            neighbourhood = self.neighbourhood_snapshot(now)
        if self.publisher:
            if neighbourhood is not None:
                self.publisher.publish_neighbourhood(neighbourhood)
            for key in self.meters:
                state = self.snapshot(int(key), now)
                if neighbourhood is not None:
                    state['vs_neighbourhood_today'] = self.comparison(int(key), state, neighbourhood)
                self.publisher.publish(int(key), state)

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
        if self.config.neighbourhood_factor is None:
            today = state['today']
        elif identifier in self.config.litres_per_count:
            today = state['today_litres']
        else:
            return None
        return today / average * 100
