"""Fit litres per pulse from matched, timestamped register and radio readings."""
import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path


def rows(path, column):
    result = {}
    with Path(path).open(newline='') as source:
        for row in csv.DictReader(source):
            stamp = datetime.fromisoformat(row['time'].replace('Z', '+00:00'))
            value = float(row[column])
            if stamp.tzinfo is None or not math.isfinite(value) or value < 0 or stamp in result:
                raise ValueError('readings require unique offset-aware times and finite nonnegative values')
            result[stamp] = value
    return result


def fit(register, counts, multiplier=1):
    times = sorted(set(register) & set(counts))
    if len(times) < 2:
        raise ValueError('need at least two exactly matched timestamps')
    first = times[0]
    xs = [counts[t] - counts[first] for t in times]
    ys = [(register[t] - register[first]) * multiplier for t in times]
    if any(b < a for values in (xs, ys) for a, b in zip(values, values[1:])):
        raise ValueError('readings must increase; unwrap counters before calibration')
    if max(xs) <= 0 or max(ys) <= 0:
        raise ValueError('need observed water use and a positive pulse difference')
    slope = sum(x*y for x, y in zip(xs, ys)) / sum(x*x for x in xs)
    residual = math.sqrt(sum((y-slope*x)**2 for x, y in zip(xs, ys)) / len(xs))
    return {'litres_per_count': slope, 'matched_readings': len(times),
            'rmse_litres': residual, 'method': 'zero-intercept least squares on changes from first reading'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('readings', help='CSV: time,register_reading,meter_count')
    parser.add_argument('--counts', help='separate CSV: time,meter_count; exact timestamps must match')
    parser.add_argument('--register-unit', choices=('L', 'm3'), default='L')
    args = parser.parse_args(argv)
    try:
        report = fit(rows(args.readings, 'register_reading'),
                     rows(args.counts or args.readings, 'meter_count'),
                     1000 if args.register_unit == 'm3' else 1)
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))
    return 0
