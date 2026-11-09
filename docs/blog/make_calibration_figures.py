#!/usr/bin/env python3
"""Render Dan's calibration figures from a read-only data directory.

  python docs/blog/make_calibration_figures.py --data-dir /private/calibration

No hourly utility observations are supplied, so the failed hourly fit is a
statistics panel, never a synthetic scatter plot. Source JSON is not published.
"""
import argparse
import hashlib
import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib.dates as mdates
from make_figures import BLUE, GREEN, INK, configure_style, plt, save
from matplotlib.patches import Patch

BRISBANE = ZoneInfo('Australia/Brisbane')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--out', type=Path, default=Path(__file__).parent / 'img')
    args = parser.parse_args()
    names = ('dan_hours.json', 'calibration.json', 'energy_status.json')
    sources = {name: (args.data_dir / name).read_bytes() for name in names}
    hours_data, fit, energy = (json.loads(sources[name]) for name in names)
    hours = sorted(hours_data['hours'].values(), key=lambda row: row['ending_utc'])
    ends = [datetime.fromisoformat(row['ending_utc']).astimezone(BRISBANE) for row in hours]
    pulses = [row['raw_units'] for row in hours]
    checks = sorted(fit['daily_checks'], key=lambda row: row['date'])
    # Use radio_litres, never the combined radio + utility-backfilled 'litres'.
    # Partial reception days and days without utility data are not whole-day checks.
    overlap = [day for day in energy['days'] if day['radio_hours'] == 24
               and day['filled_hours'] == 0 and day['pending_hours'] == 0
               and day['mywater_litres'] is not None]
    if not hours or not checks or not overlap:
        raise ValueError('Need hourly radio data, saved daily checks and complete overlap days')
    if fit['accepted'] or fit['applied']:
        raise ValueError('This panel documents a rejected, unapplied hourly fit')
    if not energy['calibrated'] or energy['litres_per_count'] != 5:
        raise ValueError('Expected the independently applied 5 L/pulse calibration')
    args.out.mkdir(parents=True, exist_ok=True)
    configure_style()
    provenance = 'Dan’s own meter; approved calibration data. Brisbane time (UTC+10).'

    fig, ax = plt.subplots(figsize=(10, 5.2))
    first = datetime.combine(ends[0].date(), time(), tzinfo=BRISBANE)
    last = datetime.combine(ends[-1].date() + timedelta(days=1), time(), tzinfo=BRISBANE)
    day = first
    while day < last:
        for start, stop, color in ((6, 10, '#eaf2f7'), (17, 21, '#eaf4ee')):
            ax.axvspan(day + timedelta(hours=start), day + timedelta(hours=stop),
                       color=color, zorder=0)
        day += timedelta(days=1)
    # Timestamp is the interval end; extend bars to its left, not into the next interval.
    ax.bar(ends, pulses, width=-45 / (24 * 60), align='edge', color=BLUE, zorder=2)
    ax.set(xlim=(first, last), ylim=(0, max(pulses) * 1.18),
           ylabel='Radio pulses per recovered hour',
           xlabel='Interval ending time · Australia/Brisbane (UTC+10) · 2026',
           title=f'My hourly pulse deltas across {len(hours)} recovered intervals')
    ax.xaxis.set_major_locator(mdates.DayLocator(tz=BRISBANE))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b', tz=BRISBANE))
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 18], tz=BRISBANE))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H', tz=BRISBANE))
    ax.tick_params(axis='x', which='minor', labelsize=8, pad=2)
    ax.tick_params(axis='x', which='major', pad=16)
    ax.legend(handles=[Patch(color='#eaf2f7', label='06–10 morning'),
                       Patch(color='#eaf4ee', label='17–21 evening')],
              loc='upper left', frameon=False, ncol=2)
    save(fig, '09-calibration-hours', args.out, provenance)

    fig, (ax, daily) = plt.subplots(2, 1, figsize=(10, 8.2))
    max_x = max(row['raw_units'] for row in checks) * 1.15
    ax.plot([0, max_x], [0, 5 * max_x], color=GREEN,
            label='Reference: litres = 5 × pulses')
    ax.scatter([row['raw_units'] for row in checks],
               [row['mywater_litres'] for row in checks], s=65, color=BLUE, zorder=3)
    for index, row in enumerate(checks):
        x, y = row['raw_units'], row['mywater_litres']
        # Divide the displayed tenths of a litre so the printed arithmetic agrees.
        # Full-precision source ratios are retained separately in provenance.
        display_litres = round(y, 1)
        label = (f"{datetime.fromisoformat(row['date']):%d %b}: "
                 f"{display_litres:.1f}/{x:g} = {display_litres/x:.2f} L/pulse")
        ax.annotate(label, (x, y), xytext=(.03, .85 - index * .24),
                    textcoords='axes fraction', color=INK, fontsize=11,
                    arrowprops={'arrowstyle': '-', 'color': '#748592'})
    ax.set(xlim=(0, max_x), ylim=(0, 5 * max_x), xlabel='Whole-day radio pulses',
           ylabel='Utility litres', title='Three saved daily checks land on 5 L/pulse')
    ax.legend(loc='lower right', frameon=False)
    positions = list(range(len(overlap)))
    daily.bar([x - .18 for x in positions], [row['radio_litres'] for row in overlap],
              width=.36, color=BLUE, label='Radio only, after × 5')
    daily.bar([x + .18 for x in positions], [row['mywater_litres'] for row in overlap],
              width=.36, color=GREEN, label='Utility daily litres')
    daily.set(xticks=positions,
              xticklabels=[f"{datetime.fromisoformat(row['date']):%d %b}" for row in overlap],
              ylabel='Litres per day', xlabel='Complete overlapping days · Brisbane · 2026',
              title='After applying 5 L/pulse: complete radio days versus utility totals')
    daily.legend(frameon=False, loc='upper right')
    daily.set_ylim(0, max(row['mywater_litres'] for row in overlap) * 1.3)
    save(fig, '10-calibration-days', args.out, provenance)

    fig, ax = plt.subplots(figsize=(10, 5.7))
    ax.axis('off')
    ax.text(.02, .96, 'The automatic hourly fit was rejected', fontsize=17,
            weight='bold', va='top', color=INK)
    ax.text(.02, .83, f"{fit['litres_per_count']:.2f} L/pulse", fontsize=28,
            weight='bold', color=BLUE)
    ax.text(.53, .85, 'Zero-intercept ordinary least squares\nClock-hour overlap weighted to radio intervals',
            fontsize=11, va='center', linespacing=1.6)
    rows = [
        ('Matched / nonzero hours', f"{fit['matched_hours']} / {fit['nonzero_hours']}", ''),
        ('R²', f"{fit['r2']:.2f}", f"required ≥ {fit['thresholds']['min_r2']:.2f}"),
        ('NRMSE', f"{fit['residual_nrmse']:.2f}", f"required ≤ {fit['thresholds']['max_nrmse']:.2f}"),
        ('RMSE', f"{fit['residual_rmse_litres']:.2f} L", ''),
    ]
    for index, (label, value, threshold) in enumerate(rows):
        y = .66 - index * .105
        ax.text(.02, y, label, fontsize=13)
        ax.text(.37, y, value, fontsize=13, weight='bold')
        ax.text(.60, y, threshold, fontsize=12)
    errors = [100 * row['relative_error'] for row in checks]
    ax.text(.02, .21, f"Daily errors at this fit: {min(errors):.1f}–{max(errors):.1f}% "
            f"(limit {100 * fit['thresholds']['max_daily_error']:g}%). Scale left unchanged.",
            fontsize=12, weight='bold')
    ax.text(.02, .10, 'No hourly utility observations are included in these source files.\n'
            'Daily utility totals cannot reconstruct use within :41-to-:41 radio intervals.',
            fontsize=12, linespacing=1.6, va='top')
    save(fig, '11-calibration-hourly-fit', args.out, provenance)

    record = {
        'sources': {name: {'sha256': hashlib.sha256(data).hexdigest()}
                    for name, data in sources.items()},
        'timezone': str(BRISBANE), 'hourly_intervals': len(hours),
        'hourly_utility_series_supplied': False,
        'daily_ratios': [{**row, 'litres_per_pulse': row['mywater_litres'] / row['raw_units']}
                         for row in checks],
        'annotation_precision': 'litres rounded to 0.1 L before division; ratio shown to 0.01 L/pulse',
        'energy_overlap_dates': [row['date'] for row in overlap],
        'energy_filter': 'radio_hours == 24, filled_hours == pending_hours == 0, utility present',
        'energy_radio_field': 'radio_litres',
        'figures': {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(args.out.glob('*calibration*.png'))},
    }
    (args.out / 'calibration-provenance.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(f"Rendered 3 calibration figures from {len(hours)} intervals, "
          f"{len(checks)} daily checks and {len(overlap)} complete overlap days.")


if __name__ == '__main__':
    main()
