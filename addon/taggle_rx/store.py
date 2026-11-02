"""Private-by-default filtering and atomic, bounded usage checkpoints."""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


class Store:
    def __init__(self, config, publisher=None, scan=None):
        self.config = config
        self.publisher = publisher
        self.scan = scan
        self.zone = ZoneInfo(config.timezone)
        self.path = Path(config.data_dir)
        self.meters = {}
        if scan is None:
            self.path.mkdir(parents=True, exist_ok=True)
            checkpoint = self.path / 'state.json'
            if checkpoint.exists():
                state = json.loads(checkpoint.read_text())
                if state.get('version') != 1:
                    raise ValueError('unsupported state version')
                self.meters = {k: v for k, v in state['meters'].items()
                               if int(k) in config.meter_ids}

    def save(self):
        fd, temporary = tempfile.mkstemp(dir=self.path, prefix='.state-')
        try:
            with os.fdopen(fd, 'w') as target:
                json.dump({'version': 1, 'meters': self.meters}, target, allow_nan=False)
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
        if self.scan is not None:
            row = {k: frame[k] for k in ('meter_id', 'snr_median_db', 'signal_level_dbfs')}
            if configured and 'counts' in frame:
                row['counts'] = frame['counts']
            self.scan(row)
            return
        if not self.config.allows(identifier):
            return
        stamp = stamp.astimezone(timezone.utc)
        if self.config.jsonl_logging:
            # Never log raw bits, frame bytes or encrypted bodies.
            row = {k: v for k, v in frame.items() if k in (
                'meter_id', 'format_bytes', 'encrypted', 'sequence', 'counts', 'flags',
                'snr_median_db', 'signal_level_dbfs', 'fec_errors')}
            row['time'] = stamp.isoformat()
            with (self.path / f'{stamp.date()}.jsonl').open('a') as target:
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
            self.counts(meter, frame, stamp)
        else:
            # Opaque frames expose diagnostics only, even after a clear-format frame.
            meter.pop('latest', None)
        self.save()
        if self.publisher:
            self.publisher.publish(identifier, self.snapshot(identifier, stamp))

    def counts(self, meter, frame, stamp):
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
            meter['total_litres'] += delta * self.config.litres_per_count.get(frame['meter_id'], 0)
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
        return result

    def refresh(self, now):
        """Republish date-dependent totals without changing the radio last-seen time."""
        if self.publisher:
            for key in self.meters:
                self.publisher.publish(int(key), self.snapshot(int(key), now))
