# Design: guided calibration (meter readings in Home Assistant)

Status: agreed with Dan (2026-11-02). Ships in 0.3.0 together with the 0.2.2-era fixes and the README/wiki rewrite (one release).

## Why this matters

The Taggle transmitter does **not** send the meter's register (the kL/litre reading on the dial). It sends a
16-bit **pulse counter** that started at some unknown value when the transmitter was fitted and wraps at 65,536.
Real-hardware check (2 Nov 2026): at no common pulse size (0.1, 0.5, 1, 2, 2.5, 5, 10, 25, 50, 100 L) does
`register ÷ pulse size mod 65536` match the radio counter, so the counter carries an arbitrary offset.

So every meter has two unknowns:

    register_litres = offset + litres_per_pulse × unwrapped_counter

Without them, users only see "pulses". Today they must solve this by hand (docs/CALIBRATION.md,
`taggle-calibrate` CSV). That is the hardest step for beginners and the one most likely to give wrong numbers
(m³ vs L, misaligned timestamps, copying someone else's factor). It is the most important feature to get right.

## User experience (target)

1. On the meter's device page, a **"Dial unit"** selector (m³ / kL / L — dials differ) and an **"Dial reading (e.g. 1597.765 or 1597.765 18:00)"** box. Type exactly what the dial shows in that unit, e.g. `1597.765` (m³) or `1597765` (L).
   Once calibrated, a reading that is ~1000× off the prediction is recognised as the other unit and the status
   suggests switching the selector (it is never silently converted).
2. A **"Calibration status"** sensor explains what happens next in plain words:
   - `Step 1 of 3 — read just after a transmission` → `Waiting for next transmission to line up your reading` →
   - `Step 2 of 3 — use 20–50 L this hour (reuse it), then read just after the NEXT transmission` →
   - `Calibrated: 5 L per pulse (±0.4%)` / `Readings disagree — check the last one` (with a reason).
3. Once calibrated: litres sensors appear automatically, plus **"Meter reading"** (absolute, matches the dial,
   `device_class: water`, `total_increasing`) — the right sensor for the Energy dashboard and for checking bills.
4. Every later reading is a free check: the status shows the difference ("dial 1,601.230 m³, predicted
   1,601.225 m³ — OK").

No restarts, no config editing, no maths.

## Lining a reading up with the radio

A reading is taken at time `t`. The radio only reports at hourly transmissions. Let the last frame before `t`
be at `t0` with counter `c0`, and the next after `t` at `t1` with `c1`.

- If `c0 == c1` and the reading is within ten minutes of a received frame, `exact: true`: count at `t` = `c0`. A recovered slot alone does not open this window.
- Otherwise the true count at `t` is somewhere in `[c0, c1]`. Store the **interval**, not a guess.
- The reading stays "pending" until the next frame arrives (status says so). Three counter slots per frame
  mean a missed transmission can still be filled from the following frame.
- Guidance in the UI/docs: "best right after a transmission or at a time nobody is using water" — but readings
  at any time still work, just with a wider interval.
- Readings entered later from a photo: the command topic accepts an explicit time (see Inputs).

## Solving

Readings `(R_i, [cmin_i, cmax_i])` with counters unwrapped onto one continuous scale.

- Two readings give bounds on litres per pulse:
  `K ∈ [ (R2−R1−res1−res2) / (cmax2 − cmin1), (R2−R1+res1+res2) / (cmin2 − cmax1) ]` when the upper denominator is positive.
- **Snap to standard pulse sizes.** Pulse outputs use standard values (0.1, 0.25, 0.5, 1, 2.5, 5, 10, 25, 50,
  100 L). If exactly one standard value lies inside the bounds, adopt it (status: "5 L per pulse — standard
  value, fits your readings"). If none does, use the interval midpoint once its relative width is ≤ 2%
  (configurable). If several do, keep waiting for more usage/readings and say why.
- Offset from the readings with exact (or narrowest) intervals; with ≥ 3 readings use least squares over
  interval midpoints, weighted by 1/width², and report residuals.
- **Plausibility checks:** reject a reading that implies negative usage, a litres-per-pulse outside
  0.05–1000 L, or a residual larger than the interval + reading resolution + 0.5% after calibration ("typo? 1579 vs 1597"); keep it
  stored but excluded, visible in status attributes, deletable.
- No minimum-usage gate: only unique standard sizes or a sufficiently narrow nonstandard bound can calibrate. Every reading contributes ± its typed resolution (1 L at three m³/kL decimals; 10 L at two; 1000 L at zero). Name all ambiguous standard candidates.
- Counter wraps: unwrap with the existing slot/sequence logic; if a gap is long enough that multiple wraps are
  possible, the register readings resolve the ambiguity (choose the wrap count consistent with K bounds).

## Inputs

- MQTT `select` entity per meter, "Dial unit": `m³` (default), `kL`, `L` (persisted; configurable default
  `dial_unit` in options). MQTT `text` entity (pattern validated) → command topic
  `taggle/<id>/reading/set` with a number in the selected unit and optional time in the same command: `1597.765 18:00`, `1597,765 1800`, `1597.765 at 6:00`, or `1597.765@18:00`. ISO with offset also works.
- Same topic also accepts JSON: `{"litres": 1597765, "time": "2026-11-02T18:00:00+10:00", "source": "photo"}` or
  `{"m3": 1597.765, ...}`. This lets users backfill a photo reading and lets an **HA automation feed utility
  readings automatically** (e.g. a MyWater/portal sensor with a `read_at` attribute). Ship an example
  automation/blueprint in the docs.
- MQTT `button` "Delete all dial readings" (Configuration, mdi:delete-sweep) (with confirmation in docs) and per-reading delete via the attributes list
  (JSON command `{"delete": <reading id>}`).
- Config `litres_per_count` stays as a manual override ("pinned"); when set, guided calibration only validates
  and reports, never changes the factor. Optional `meter_reading_offset` pin for completeness.

## Outputs (per meter)

| Entity | Notes |
| --- | --- |
| `select.taggle_<id>_dial_unit` | m³ / kL / L |
| `text.taggle_<id>_dial_reading` | input box (state = last entered value) |
| `sensor.taggle_<id>_calibration_status` | text state + attributes: readings list (time, value, count interval, used/excluded, residual), K bounds, chosen K, method (standard value / fit / pinned), offset |
| `sensor.taggle_<id>_meter_reading` | absolute L (or m³ display precision 3); appears once calibrated |
| existing `*_litres` sensors | now enabled automatically once calibrated |
| `button.taggle_<id>_reset_calibration` | clears readings |

Neighbourhood: default neighbour factor continues to follow the first meter's factor (now auto-calibrated).

## Persistence and history

- Readings and solution persist in `state.json` (0600), versioned. Past `total_litres` is not revalued
  (unchanged rule); the new absolute `meter_reading` is consistent from calibration onward.
- Logged at INFO: reading accepted / pending / solved / rejected — configured meter only.

## Card

- Status line under the meter: "Calibrated 5 L/pulse" or a friendly prompt "Enter your dial reading to show
  litres" linking to the device page; show the absolute meter reading when available.

## Documentation

- README "Turn pulses into litres": 3 steps with pictures — read the dial (register-dial.svg + a real dial photo,
  ID blurred), type it in, use 20–50 L this hour (reuse it), read after the next transmission, done. Manual route moves to the wiki Calibration page.
- Wiki Calibration: how alignment works, standard pulse sizes, utility-feed automation example, troubleshooting
  (m³ vs L, typo detection, wrong meter ID).

## Tests

- Synthetic: exact readings; interval readings; readings across wraps; long gaps; typo detection; units; pinned
  factor; reset; restart persistence; JSON with explicit time; out-of-order entry.
- Real fixture from the 2 Nov 2026 test (IDs fictionalised): R1 = 1,597,361 L at 02:43 with a static counter
  (exact), R2 ≈ 1,597,765 L at 18:00 inside a 35-pulse hour → K ∈ [4.02, 6.25] (including ±1 L resolution per reading) L, 5 L is the only standard
  value inside → adopt 5 L; then validate against the 3 Nov utility reading.
- Live: run in the test VM against the real meter with the photo reading and the next MyWater reading.

## Decisions

Decided: both units via a selector (m³ default); auto-apply when exactly one standard pulse size fits and show
it in the status; one release (0.3.0).

The read-now binary sensor (`binary_sensor.taggle_<id>_read_dial_now`) is ON for ten minutes after a configured-meter frame, with since/until/next_transmission attributes. Readings outside the window remain accepted, less precise; take fallback readings about a day apart. Exactness requires the window plus a static count bracket. Upgrade deletes both legacy control discovery records and drops pending photo time.
