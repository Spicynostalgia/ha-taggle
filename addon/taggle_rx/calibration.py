"""Guided dial calibration. Never replace an unknown counter interval with a guess."""
import itertools
import json
import math
import re
import statistics
from datetime import datetime, timedelta, timezone
from decimal import Decimal

STANDARDS = (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50, 100)
UNITS = {'m3': 1000, 'm³': 1000, 'kL': 1000, 'kl': 1000, 'L': 1, 'litres': 1}
LABELS = {'m3': 'm³', 'kl': 'kL', 'litres': 'L'}
MODULUS = 65536
READ_WINDOW_SECONDS = 600
NUMBER = r'(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)'
CLOCK = r'(?:[01]?[0-9]|2[0-3]):[0-5][0-9]|(?:[01][0-9]|2[0-3])[0-5][0-9]'
ISO_TIME = r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]+)?)?(?:Z|[+-][0-9]{2}:?[0-9]{2})'
READING_PATTERN = rf'^\s*({NUMBER})(?:(?:\s+(?:at\s+)?|\s*@\s*)({CLOCK}|{ISO_TIME}))?\s*$'


def initial(unit='m3'):
    return {'dial_unit': LABELS.get(unit, unit), 'readings': [],
            'next_id': 1, 'slots': {}, 'solution': None, 'status': 'Needs 2 readings'}


def migrate(meter, unit):
    """Recover the contiguous tail of v1 checkpoints without inventing missing hours."""
    cal = initial(unit)
    latest = meter.get('latest')
    if not latest:
        return cal
    index, raw = latest['index'], latest['raw_count']
    stamp = datetime.fromisoformat(latest['time'])
    history = cal['slots']
    history[str(index)] = {'time': stamp.isoformat(), 'raw': raw}
    while str(index) in meter['hours']:
        hour = meter['hours'][str(index)]
        raw = (raw - hour['counts']) % MODULUS
        stamp = datetime.fromisoformat(hour['end']) - timedelta(hours=1)
        index -= 1
        history[str(index)] = {'time': stamp.isoformat(), 'raw': raw}
    ordered = sorted(history, key=int)
    count = history[ordered[0]]['raw']
    history[ordered[0]]['count'] = count
    for a, b in zip(ordered, ordered[1:]):
        count += (history[b]['raw'] - history[a]['raw']) % MODULUS
        history[b]['count'] = count
    return cal


def timestamp(value, now, zone):
    if value is None or value == '':
        return now
    if not isinstance(value, str):
        raise ValueError('Reading time must be HH:MM or ISO-8601 with a UTC offset')
    if re.fullmatch(r'[0-9]{1,2}:[0-9]{2}|[0-9]{4}', value):
        hour, minute = map(int, value.split(':') if ':' in value else (value[:2], value[2:]))
        local = now.astimezone(zone).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if local > now:  # 23:50 typed at 00:05 means last night's photo
            local = (local - timedelta(days=1)).replace(hour=hour, minute=minute)
        # A clock time inside a DST jump cannot describe a photo.
        if local.astimezone(timezone.utc).astimezone(zone).replace(fold=0) != local.replace(fold=0):
            raise ValueError('This local time does not exist; use ISO-8601 with a UTC offset')
        if local.replace(fold=0).utcoffset() != local.replace(fold=1).utcoffset():
            raise ValueError('This local time occurs twice; use ISO-8601 with a UTC offset')
        return local.astimezone(timezone.utc)
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('Use HH:MM for today, or ISO-8601 with a UTC offset') from error
    if stamp.tzinfo is None:
        raise ValueError('ISO reading time must include a UTC offset')
    return stamp.astimezone(timezone.utc)


def intake(cal, payload, now, zone):
    """Validate a command before mutating state; return its accepted action."""
    match = re.fullmatch(READING_PATTERN, payload)
    when = None
    if match:
        amount_text, when = match.groups()
        value = Decimal(amount_text.replace(',', '.'))
    else:
        try:
            value = json.loads(payload, parse_float=Decimal)
        except json.JSONDecodeError as error:
            raise ValueError('Use a dial reading, optionally followed by a time: 1597.765 18:00') from error
    if isinstance(value, dict):
        if value == {'reset': True}:
            unit, history = cal['dial_unit'], cal['slots'] if not cal.get('blocked') else {}
            gaps = cal.get('gaps', []) if history else []
            next_id = cal['next_id']
            timing = {k: cal[k] for k in ('last_frame', 'transmission', 'cadence_intervals') if k in cal}
            cal.clear()
            cal.update(initial(unit))
            cal['slots'] = history
            cal['gaps'] = gaps
            cal['next_id'] = next_id
            cal.update(timing)
            return 'reset'
        if set(value) == {'delete'}:
            identifier = value['delete']
            if isinstance(identifier, bool) or not isinstance(identifier, int):
                raise ValueError('Delete requires a reading ID from the status attributes')
            rows = [r for r in cal['readings'] if r['id'] != identifier]
            if len(rows) == len(cal['readings']):
                raise ValueError('Reading ID not found')
            cal['readings'] = rows
            cal['solution'] = None
            return 'deleted'
        units = set(value) & {'litres', 'm3', 'kl'}
        if len(units) != 1 or set(value) - {'litres', 'm3', 'kl', 'time', 'source'}:
            raise ValueError('Use exactly one of litres, m3 or kl, with optional time and source')
        unit = next(iter(units))
        amount = value[unit]
        source = value.get('source', 'manual')
        when = value.get('time')
    else:
        amount, unit, source = value, cal['dial_unit'], 'manual'
    if isinstance(amount, bool) or not isinstance(amount, (int, float, Decimal)) or not math.isfinite(amount) or amount < 0:
        raise ValueError('Enter a finite, nonnegative dial reading')
    resolution = 10.0 ** Decimal(str(amount)).as_tuple().exponent * UNITS[unit]
    if not math.isfinite(resolution) or resolution <= 0:
        raise ValueError('Reading precision is out of range')
    amount = float(amount)
    litres = amount * UNITS[unit]
    if not math.isfinite(litres) or litres > 1e15:
        raise ValueError('Dial reading is too large; check the unit')
    if not isinstance(source, str) or len(source) > 100:
        raise ValueError('Reading source must be text up to 100 characters')
    stamp = timestamp(when, now, zone)
    if stamp > now:
        raise ValueError('Reading time is in the future; check the photo time and timezone')
    if len(cal['readings']) >= 200:
        raise ValueError('200 readings stored; delete an older reading before adding another')
    cal['readings'].append({'id': cal['next_id'], 'time': stamp.isoformat(), 'litres': litres,
                            'value': amount, 'unit': LABELS.get(unit, unit),
                            'source': source, 'resolution_litres': resolution, 'exact': False,
                            'used': False, 'count_interval': None})
    cal['next_id'] += 1
    cal['last_entered_litres'] = litres
    cal['last_entry'] = payload.strip() if match else str(amount)
    cal.pop('error', None)
    return 'accepted'


def slots(cal, frame, stamp, index):
    """Use Store's sequence-derived slot identities, including the two recovered slots."""
    previous = cal.get('transmission')
    if previous is None or index > previous['index']:
        intervals = cal.setdefault('cadence_intervals', [])
        if previous:
            seconds = (stamp - datetime.fromisoformat(previous['time'])).total_seconds()
            intervals.append(seconds / (index - previous['index']))
            del intervals[:-12]
        cal['transmission'] = {'time': stamp.isoformat(), 'index': index,
                               'interval_seconds': statistics.median(intervals) if intervals else 3600}
    history = cal['slots']
    history.setdefault(str(index), {'time': stamp.isoformat(), 'raw': frame['counts'][0]})['received'] = True
    for age in (2, 1, 0):
        key = str(index - age)
        if key not in history:
            history[key] = {'time': (stamp - timedelta(hours=age)).isoformat(),
                            'raw': frame['counts'][age]}
    ordered = sorted(history, key=int)
    first = history[ordered[0]]
    count = first.get('count', first['raw'])
    first['count'] = count
    for before, after in zip(ordered, ordered[1:]):
        count += (history[after]['raw'] - history[before]['raw']) % MODULUS
        history[after]['count'] = count
    cal['gaps'] = sorted(set(cal.get('gaps', [])) |
                         {int(b) for a, b in zip(ordered, ordered[1:]) if int(b) - int(a) > 1})
    cutoff = stamp - timedelta(days=90)
    # Readings keep their original brackets even after the rolling history expires.
    cal['slots'] = {k: v for k, v in history.items() if datetime.fromisoformat(v['time']) >= cutoff}


def align(cal):
    history = sorted(cal['slots'].items(), key=lambda item: int(item[0]))
    for row in cal['readings']:
        row.setdefault('resolution_litres', 1.)
        row.setdefault('exact', False)
        stamp = datetime.fromisoformat(row['time'])
        before = [(k, v) for k, v in history if datetime.fromisoformat(v['time']) <= stamp]
        after = [(k, v) for k, v in history if datetime.fromisoformat(v['time']) >= stamp]
        if before and after:
            left, right = before[-1], after[0]
            row['bracket'] = [int(left[0]), int(right[0])]
            row['base_interval'] = [left[1]['count'], right[1]['count']]
            row['count_interval'] = row['base_interval'][:]
            elapsed = (stamp - datetime.fromisoformat(left[1]['time'])).total_seconds()
            row['exact'] = (0 <= elapsed < READ_WINDOW_SECONDS and left[1].get('received', False)
                            and left[1]['count'] == right[1]['count'])
        elif not row.get('base_interval'):
            row['reason'] = ('Waiting for next transmission to line up your reading' if before else
                             'No counter history before this reading; enter a newer dial reading')


def bounds(rows):
    low, high = .05, 1000.
    for a, b in itertools.combinations(rows, 2):
        usage = b['litres'] - a['litres']
        amin, amax = a['count_interval']
        bmin, bmax = b['count_interval']
        maximum, minimum = bmax - amin, bmin - amax
        resolution = a.get('resolution_litres', 1) + b.get('resolution_litres', 1)
        lower, upper = usage - resolution, usage + resolution
        if maximum == 0 and lower <= 0 <= upper:
            continue
        if upper < 0 or maximum <= 0:
            return None
        low = max(low, lower / maximum)
        if minimum > 0:
            high = min(high, upper / minimum)
    if low > high and low - high <= 1e-10 * max(1, low, high):
        low = high = (low + high) / 2
    return (low, high) if low <= high and high > 0 else None


def regression(rows, factor=None):
    # Exact intervals get one pulse of weight; this avoids infinite weights.
    weights = [1 / max(1, r['count_interval'][1] - r['count_interval'][0]) ** 2 for r in rows]
    counts = [sum(r['count_interval']) / 2 for r in rows]
    centre = sum(w * c for w, c in zip(weights, counts)) / sum(weights)
    mean = sum(w * r['litres'] for w, r in zip(weights, rows)) / sum(weights)
    if factor is None:
        denominator = sum(w * (c - centre) ** 2 for w, c in zip(weights, counts))
        if denominator <= 0:
            return None, None
        factor = sum(w * (c - centre) * (r['litres'] - mean)
                     for w, c, r in zip(weights, counts, rows)) / denominator
    # With two readings anchor the offset to the narrowest interval.
    if len(rows) < 3:
        anchor = min(rows, key=lambda r: r['count_interval'][1] - r['count_interval'][0])
        offset = anchor['litres'] - factor * sum(anchor['count_interval']) / 2
    else:
        offset = mean - factor * centre
    # Ensure the chosen offset fits every retained interval, when feasible.
    lower = max(r['litres'] - r.get('resolution_litres', 1) - factor * r['count_interval'][1] for r in rows)
    upper = min(r['litres'] + r.get('resolution_litres', 1) - factor * r['count_interval'][0] for r in rows)
    if lower <= upper:
        offset = max(lower, min(upper, offset))
    return factor, offset


def hypotheses(cal, rows, factor=None):
    """Enumerate extra wraps only at missing slots, bounded by measured usage.

    Too many possibilities is an explicit ambiguity, never a guessed wrap count.
    """
    start, end = rows[0]['bracket'][0], rows[-1]['bracket'][1]
    gaps = [b for b in cal.get('gaps', []) if start < b <= end]
    usage = (rows[-1]['litres'] - rows[0]['litres'] + rows[-1].get('resolution_litres', 1)
             + rows[0].get('resolution_litres', 1))
    minimum = rows[-1]['base_interval'][0] - rows[0]['base_interval'][1]
    limit = max(0, math.floor((max(0, usage) / (factor or .05) - minimum + 1e-7) / MODULUS))
    if (limit + 1) ** len(gaps) > 4096:
        cal['wrap_search_limited'] = True
        return []
    candidates = []
    for wraps in itertools.product(range(limit + 1), repeat=len(gaps)):
        intervals = [[base + MODULUS * sum(w for g, w in zip(gaps, wraps) if g <= edge)
                      for base, edge in zip(r['base_interval'], r['bracket'])] for r in rows]
        trial = [dict(r, count_interval=i) for r, i in zip(rows, intervals)]
        interval = bounds(trial)
        if interval:
            candidates.append((trial, interval, {str(g): w for g, w in zip(gaps, wraps)}))
    return candidates


def equivalent(candidates):
    """Ignore wrap placement only when every reading has identical counter bounds."""
    unique = {}
    for trial, interval, wraps, k in candidates:
        key = (k, tuple(tuple(r['count_interval']) for r in trial))
        unique.setdefault(key, (trial, interval, wraps, k))
    return list(unique.values())


def solve(cal, config, identifier, now=None, zone=timezone.utc):
    now = now or datetime.now(timezone.utc)
    if cal.get('blocked'):
        cal['solution'] = None
        cal['status'] = 'Counter sequence changed — reset calibration and enter fresh readings'
        return
    cal['wrap_search_limited'] = False
    align(cal)
    old = cal.get('solution')
    pinned = config.litres_per_count.get(identifier)
    offset_pin = config.meter_reading_offset.get(identifier)
    if pinned is not None:
        cal['solution'] = {'factor': pinned, 'offset': offset_pin if offset_pin is not None else
                           old.get('offset') if old and old['factor'] == pinned else None,
                           'method': 'pinned', 'bounds': None, 'uncertainty': None,
                           'wraps': old.get('wraps', {}) if old else {}}
    elif old and old['method'] == 'pinned':
        cal['solution'] = old = None
    rows = []
    for row in sorted(cal['readings'], key=lambda r: (r['time'], r['id'])):
        row['used'] = False
        row.pop('residual_litres', None)
        if not row.get('base_interval'):
            continue
        row.pop('reason', None)
        row['count_interval'] = row['base_interval'][:]
        solution = cal.get('solution')
        if solution:
            row['count_interval'] = [base + MODULUS * sum(int(w) for g, w in solution.get('wraps', {}).items()
                                                        if int(g) <= edge)
                                     for base, edge in zip(row['base_interval'], row['bracket'])]
        if rows and solution:
            matches = [(trial, wraps) for trial, interval, wraps in hypotheses(cal, rows + [row], solution['factor'])
                       if interval[0] - 1e-10 <= solution['factor'] <= interval[1] + 1e-10]
            if matches:
                row['count_interval'] = [min(t[-1]['count_interval'][0] for t, _ in matches),
                                         max(t[-1]['count_interval'][1] for t, _ in matches)]
        if rows and row['litres'] < rows[-1]['litres']:
            row['reason'] = 'Negative usage — check the digits or dial unit'
        if solution and solution['offset'] is not None:
            factor, offset = solution['factor'], solution['offset']
            predicted = offset + factor * sum(row['count_interval']) / 2
            tolerance = factor * (row['count_interval'][1] - row['count_interval'][0]) / 2
            reference = rows[0]['litres'] if rows else row['litres']
            tolerance += row.get('resolution_litres', 1) + max(
                (r.get('resolution_litres', 1) for r in rows), default=0) + abs(predicted - reference) * .005
            residual = row['litres'] - predicted
            row['residual_litres'] = residual
            if abs(residual) > tolerance:
                ratio = row['litres'] / predicted if predicted else 0
                row['reason'] = ('Reading is about 1000× off — switch Dial unit (m³/kL versus L)'
                                 if .0009 <= ratio <= .0011 or 900 <= ratio <= 1100 else row.get('reason') or
                                 'Dial and prediction disagree — check for a typo or wrong meter ID')
        if not row.get('reason') and rows and bounds([rows[0], row]) is None:
            # A missing-slot gap might contain extra wraps; let hypotheses resolve it.
            if not hypotheses(cal, [rows[0], row]) and not cal['wrap_search_limited']:
                row['reason'] = 'Implausible litres per pulse (outside 0.05–1000 L); check digits and unit'
        if not row.get('reason'):
            row['used'] = True
            rows.append(row)
    cal['bounds'] = None
    if len(rows) >= 2:
        fixed = pinned if pinned is not None else old['factor'] if old and old['method'] == 'standard value' else None
        candidates = hypotheses(cal, rows, fixed)
        standard = [(trial, interval, wraps, k) for trial, interval, wraps in candidates
                    for k in STANDARDS if interval[0] - 1e-12 <= k <= interval[1] + 1e-12]
        if cal['wrap_search_limited'] and fixed is None:
            # Standard factors sharply bound the number of wraps and can still be
            # decisive when searching the entire plausible factor range is too large.
            standard = [(t, b, w, k) for k in STANDARDS for t, b, w in hypotheses(cal, rows, k)
                        if b[0] - 1e-12 <= k <= b[1] + 1e-12]
        standard = equivalent(standard)
        chosen = None
        ambiguous_factor = None
        if fixed is not None:
            matches = [(t, b, w, fixed) for t, b, w in candidates if b[0] - 1e-12 <= fixed <= b[1] + 1e-12]
            matches = equivalent(matches)
            if len(matches) == 1:
                chosen = matches[0]
        elif len(standard) == 1:
            chosen = standard[0]
        elif standard and len({c[3] for c in standard}) == 1:
            ambiguous_factor = standard[0][3]
        elif not standard and len(candidates) == 1:
            trial, interval, wraps = candidates[0]
            midpoint = sum(interval) / 2
            if (interval[1] - interval[0]) / midpoint <= config.calibration_max_uncertainty:
                k = regression(trial)[0] if len(rows) >= 3 else midpoint
                chosen = (trial, interval, wraps, max(interval[0], min(interval[1], k)))
        if len(candidates) == 1:
            cal['bounds'] = list(candidates[0][1])
        if chosen:
            trial, interval, wraps, k = chosen
            cal['bounds'] = list(interval)
            k, offset = regression(trial, k)
            if offset_pin is not None:
                offset = offset_pin
            method = 'pinned' if pinned is not None else 'standard value' if k in STANDARDS else 'fit'
            cal['solution'] = {'factor': k, 'offset': offset, 'method': method, 'bounds': list(interval),
                               'uncertainty': (interval[1] - interval[0]) / (interval[1] + interval[0]),
                               'wraps': wraps}
            for row, aligned in zip(rows, trial):
                row['count_interval'] = aligned['count_interval']
        elif ambiguous_factor is not None:
            cal['solution'] = {'factor': ambiguous_factor, 'offset': None, 'method': 'standard value',
                               'bounds': None, 'uncertainty': None, 'wraps': {}, 'ambiguous': True}
        elif not chosen:
            if pinned is not None:
                cal['error'] = 'Readings disagree — the pinned factor does not fit; check digits, unit and factor'
            sizes = sorted({c[3] for c in standard})
            names = [f'{k:g} L' for k in sizes]
            joined = ' and '.join(names) if len(names) <= 2 else ', '.join(names[:-1]) + ' and ' + names[-1]
            next_time = attributes(cal, now, zone)['next_transmission']
            clock = datetime.fromisoformat(next_time).strftime('%H:%M') if next_time else 'time not yet known'
            cal['status'] = (f'{joined} per pulse {"both" if len(sizes) == 2 else "all"} fit — '
                             f'take another reading, ideally just after the next transmission (≈ {clock})'
                             if len(sizes) > 1 else
                             'Several wrap counts fit — read again just after a transmission' if
                             standard or len(candidates) > 1 or cal['wrap_search_limited'] else
                             'Readings are too uncertain — read again just after a transmission')
        if (pinned is None and all(r.get('exact') for r in rows)
                and abs(rows[-1]['litres'] - rows[0]['litres']) <= sum(
                    r.get('resolution_litres', 1) for r in (rows[0], rows[-1]))
                and rows[-1]['base_interval'][1] == rows[0]['base_interval'][0]):
            cal['solution'] = None
            cal['status'] = ('No water was used between your readings — use some water before the next '
                             'transmission, then read again.')
    elif rows:
        if pinned is not None:
            _, offset = regression(rows, pinned)
            cal['solution']['offset'] = offset_pin if offset_pin is not None else offset
        cal['status'] = routine(cal, now, zone)
    else:
        cal['status'] = routine(cal, now, zone)
    solution = cal.get('solution')
    if solution:
        factor, offset = solution['factor'], solution['offset']
        for row in rows:
            if offset is not None:
                row['residual_litres'] = row['litres'] - offset - factor * sum(row['count_interval']) / 2
        cal['status'] = (f'Calibrated: {factor:g} L per pulse — ' +
                         ('standard value, fits your readings' if solution['method'] == 'standard value' else
                          'pinned in configuration' if pinned is not None else
                          f'fit (±{solution["uncertainty"] * 100:.1f}%)'))
        if rows and offset is not None:
            last = max(rows, key=lambda r: r['id'])
            predicted = last['litres'] - last['residual_litres']
            scale = UNITS[cal['dial_unit']]
            cal['last_check'] = (f'Dial {last["litres"] / scale:,.3f} {cal["dial_unit"]}, '
                                 f'predicted {predicted / scale:,.3f} {cal["dial_unit"]} — OK')
            if len(rows) >= 3:
                cal['status'] += ' · ' + cal['last_check']
    cal['unresolved_gap'] = False
    if solution:
        if solution.get('ambiguous'):
            cal['status'] += ' · Read just after a transmission to resolve the absolute reading'
        covered = max((r['bracket'][1] for r in rows), default=-math.inf)
        cal['unresolved_gap'] = any(g > covered and str(g) not in solution.get('wraps', {})
                                    for g in cal.get('gaps', []))
        if cal['unresolved_gap']:
            cal['status'] = 'Counter gap may hide wraps — enter a new dial reading to check the absolute reading'
    pending = [r for r in cal['readings'] if not r.get('base_interval')]
    excluded = [r for r in cal['readings'] if r.get('base_interval') and not r['used']]
    if pending:
        cal['status'] = (routine(cal, now, zone).split(' Outside the window')[0] +
                         ' Waiting for next transmission to line up your reading.'
                         if len(cal['readings']) == 1 and pending[-1]['reason'].startswith('Waiting')
                         else pending[-1]['reason'])
    if excluded:
        cal['status'] = 'Readings disagree — check the last one: ' + excluded[-1]['reason']
    if cal.get('error'):
        cal['status'] = cal['error']


def read_window(cal, now, next_time=None):
    frame_time = cal.get('last_frame') or cal.get('transmission', {}).get('time')
    since = datetime.fromisoformat(frame_time) if frame_time else None
    until = since + timedelta(seconds=READ_WINDOW_SECONDS) if since else None
    return {'state': 'ON' if since and since <= now < until else 'OFF',
            'since': since.isoformat() if since else None,
            'until': until.isoformat() if until else None, 'next_transmission': next_time}


def routine(cal, now, zone):
    attrs = attributes(cal, now, zone)
    window = read_window(cal, now)
    next_time = attrs['next_transmission']
    clock = datetime.fromisoformat(next_time).strftime('%H:%M') if next_time else 'time not yet known'
    if (window['state'] == 'ON' and (not cal['readings'] or
            datetime.fromisoformat(window['since']) > datetime.fromisoformat(cal['readings'][0]['time']))):
        minutes = int((now - datetime.fromisoformat(window['since'])).total_seconds() // 60)
        return (f'Read your dial now — a transmission arrived {minutes} min ago. '
                f'Step {3 if cal["readings"] else 1} of 3 — read within 10 minutes, before anyone uses water.')
    if cal['readings']:
        return (f'Step 2 of 3 — use some water this hour (20–50 L; reuse it), then just after the NEXT '
                f'transmission (≈ {clock}) read again. Outside the window is less precise; '
                'readings about a day apart may need a third reading.')
    return (f'Step 1 of 3 — wait for the next transmission (≈ {clock}), then read your dial within '
            '10 minutes, before anyone uses water.')


def attributes(cal, now, zone):
    history = sorted(cal['slots'].values(), key=lambda v: v['time'])
    next_time = None
    transmission = cal.get('transmission', {})
    interval = transmission.get('interval_seconds', 3600)
    if history:
        last = datetime.fromisoformat(transmission.get('time', history[-1]['time']))
        steps = max(1, math.floor((now - last).total_seconds() / interval) + 1)
        next_time = (last + timedelta(seconds=steps * interval)).astimezone(zone)
    solution = cal.get('solution') or {}
    # Last 10 only: Home Assistant stops recording attributes over 16 KB.
    return {'readings': cal['readings'][-10:], 'reading_count': len(cal['readings']), 'k_bounds': cal.get('bounds'),
            'chosen_k': solution.get('factor'), 'method': solution.get('method'),
            'offset': solution.get('offset'), 'uncertainty': solution.get('uncertainty'),
            'dial_unit': cal['dial_unit'], 'transmit_interval_seconds': interval,
            'transmit_minute': next_time.minute if next_time else None,
            'next_transmission': next_time.isoformat() if next_time else None,
            'next_transmission_expected': ('Next transmission expected ≈ ' + next_time.strftime('%H:%M')
                                           if next_time else 'Waiting to learn the transmission time'),
            'last_check': cal.get('last_check'), 'unresolved_gap': cal.get('unresolved_gap', False),
            'wrap_search_limited': cal.get('wrap_search_limited', False),
            'read_dial_now': read_window(cal, now, next_time.isoformat() if next_time else None),
            'delete_all_dial_readings': ('Delete all dial readings clears readings and automatic calibration; '
                                         'keeps units, usage totals and configuration pins.'),
            'guidance': ('Read within 10 minutes after a transmission, before water use. Use 20–50 L this hour '
                         '(reuse it), then read just after the next transmission. Outside the window is less '
                         'precise; use readings about a day apart; a third reading may be needed.')}
