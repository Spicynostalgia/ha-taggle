# Calibrate litres per count

Keep raw pulses until you have measured a scale. A manufacturer's count, physical register litre and utility export value may represent different units or different interval boundaries.

1. Confirm the transmitter ID from your own label and record reliable reception.
2. Take a physical register reading at a radio update and record the receiver's cumulative `meter_count` at that same endpoint. Repeat after enough use to exceed register rounding. A utility export can supply equivalent register readings if its timestamps and units are known.
3. Use only intervals without missing receiver hours or a counter reset. Radio intervals need not end on a clock hour. Do not match a clock-hour export to a nearby radio interval by rounding timestamps.
4. Prepare a CSV with offset-aware ISO timestamps and decimal register units:

```csv
time,register_reading,meter_count
2026-01-01T12:15:00Z,10.000,100
2026-01-02T12:15:00Z,10.250,200
2026-01-03T12:15:00Z,10.625,350
```

```sh
taggle-calibrate readings.csv --register-unit m3
```

This fictional example gives **2.5 L/count**. With only two readings, the calculation is `(register_end - register_start) / (counts_end - counts_start)`, converting m³ to litres first. For more readings the helper fits changes from the first reading using least squares through zero, and reports RMSE in litres. Duplicate/naive timestamps, nonfinite values, nonincreasing usable ranges and backwards readings are rejected.

A register-only CSV can have `time,register_reading` columns; supply a second `time,meter_count` file with `--counts counts.csv`. Only exactly matching timestamps participate. The CLI never scrapes a portal, uses credentials or writes a scale to your configuration.

A small residual alone does not prove the scale. Validate it over several independent days, including low and high usage, and compare totals. An exact fit from two observations has no independent validation. For exports of interval litres rather than cumulative register readings, first form aligned cumulative values over complete intervals; the helper does not infer sub-hour use.

Set the verified factor in standalone JSON:

```json
"litres_per_count": {"123456": 2.5}
```

Or in add-on options:

```yaml
litres_per_count:
  - meter_id: 123456
    value: 2.5
```

Restart and select `sensor.taggle_123456_total_litres` in Home Assistant's Energy water configuration. Calibration creates litre entities with the water device class. The cumulative litre entity adds newly observed intervals at the factor active when they arrive, preserving its baseline through factor changes. It does not retroactively add pre-calibration usage. Hourly and daily displays use the currently configured factor.
