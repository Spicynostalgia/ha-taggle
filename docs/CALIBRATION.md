# Calibrate litres per count

Keep raw pulses until you have measured a scale. A manufacturer's count, physical register litre and utility export value may represent different units or different interval boundaries.

## Reading your dial

![Illustration: black whole-kL wheels, red fractional digits and pointer dials, plus the star flow indicator](images/register-dial.svg)

*Illustration of a typical mechanical register, not a photo. Layouts vary: always read the units and multipliers printed on your meter.*

- **Black digit wheels:** commonly whole kilolitres, labelled **kL** or **m³**. These units mean the same volume: **1 kL = 1 m³ = 1,000 L**.
- **Red digits and/or small red pointer dials:** fractions of a cubic metre. **×0.1 = 100 L**, **×0.01 = 10 L**, **×0.001 = 1 L** when the register unit is m³/kL. Do not add pointer fractions again if the red digits already show them.
- **Small fast-spinning star/leak indicator:** shows small flows; it is not the cumulative volume reading. Movement when everything is off can help identify a leak.

In the fictional digit example, **`01234 | 567` → 1234.567 m³ → 1,234,567 L**. Photograph the whole register face so its printed units and decimal positions remain visible. The **meter serial number** identifies the hardware; it is not the register reading, transmitter ID or receiver `meter_count`.

## Record aligned readings

1. Confirm the transmitter ID from your own label and record reliable reception.
2. Wait for a **fresh transmission** (`last_seen` just updated). Note that timestamp and the receiver's cumulative **`meter_count`**. Go straight to the meter box and photograph the register; retain the phone photo timestamp as the actual physical reading time. Avoid all water use between the radio endpoint and the photo so they represent the same reading. If the frame was delayed/old or water was used in between, take another aligned pair.
3. Use water normally for **a day or more**, aiming for **at least 1,000 L of normal use** so register rounding matters less. Wait longer if necessary; do not run water just to reach the target. Repeat the fresh-transmission/photo procedure.
4. Check there are **no missing receiver hours or counter resets** across the whole period. A utility export can supply equivalent register readings if its timestamps and units are known. Radio intervals need not end on a clock hour; do not align an export by rounding its time to a nearby radio endpoint.

Keep both original timestamps. Only assign the register reading to the radio endpoint in the calibration CSV when no intervening use means the readings really align; the helper cannot correct a delay or estimate water used between them.

## Calculate and validate the scale

For two aligned readings, first convert the physical register values to litres:

```text
litres_per_count = (reading2_L - reading1_L) / (meter_count2 - meter_count1)
```

Fictional worked example: **1234.567 → 1235.892 m³** gives **1,325 L**. Receiver `meter_count` **10,000 → 10,530** gives **530 counts**. The scale is **1,325 / 530 = 2.5 L/count**. This is an example, not a default for your meter.

For **three or more aligned readings**, prepare a CSV with offset-aware ISO timestamps and decimal register units:

```csv
time,register_reading,meter_count
2026-01-01T12:15:00Z,1234.567,10000
2026-01-02T12:15:00Z,1235.892,10530
2026-01-03T12:15:00Z,1237.217,11060
```

```sh
taggle-calibrate readings.csv --register-unit m3
```

This fictional example gives **2.5 L/count**. With only two readings, the calculation is `(register_end - register_start) / (counts_end - counts_start)`, converting m³ to litres first. For more readings the helper fits changes from the first reading using least squares through zero, and reports RMSE in litres. Duplicate/naive timestamps, nonfinite values, nonincreasing usable ranges and backwards readings are rejected.

A register-only CSV can have `time,register_reading` columns; supply a second `time,meter_count` file with `--counts counts.csv`. Only exactly matching timestamps participate. The CLI never scrapes a portal, uses credentials or writes a scale to your configuration.

A small residual alone does not prove the scale. Validate it over several independent days, including low and high usage, and compare totals. An exact fit from two observations has no independent validation. For exports of interval litres rather than cumulative register readings, first form aligned cumulative values over complete intervals; the helper does not infer sub-hour use.

**Quick bucket sanity check:** just after a transmission, with nothing else using water, fill a known volume (for example **2 × 10 L**). At the next hourly update, `last_hour × factor` should be approximately **20 L**. Pulse resolution and interval boundaries make this coarse; repeat or check the following interval if necessary. Reuse the water. **Do not calibrate from the bucket check alone.**

**Pitfalls:** missing hours make observed counts incomplete; a counter reset invalidates the comparison; a serial number is not a volume; m³ and litres differ by 1,000. The receiver handles a single modulo wrap between adjacent 16-bit raw slots but cannot distinguish multiple wraps. Its cumulative `meter_count` is an observed total, not the physical register. Reject suspect intervals rather than fitting across these problems.

## Apply the verified factor

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
