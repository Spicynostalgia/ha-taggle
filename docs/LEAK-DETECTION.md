# Possible leak alert

This is a **hint, not an alarm or a confirmed leak**. The receiver sees hourly
pulse totals only, not instantaneous flow. A dripping tap using **less than one
pulse per hour is invisible** to these rules. Scheduled irrigation, pool filling,
and normal overnight use can trigger them. Check the physical meter and household
usage before drawing conclusions; adjust the night window to avoid irrigation
schedules.

Detection is enabled by default for **configured meters only**, never neighbours.
It needs supported clear-format usage intervals; encrypted meters cannot provide
this hint. No litres-per-count calibration is required.

## Options

These options work in add-on configuration and standalone JSON. Set `timezone` to
your local IANA zone, for example `Australia/Brisbane` or `Australia/Sydney`.

| Option | Default | Meaning |
| --- | --- | --- |
| `leak_detection` | `true` | Enable possible-leak discovery and evaluation. `false` removes its retained discovery and hint topic on reconnect/restart. |
| `leak_continuous_hours` | `24` | Positive-flow coverage horizon, integer 1–168 hours (within the existing eight-day history). |
| `leak_night_start` | `"01:00"` | Inclusive local start time, strict 24-hour `HH:MM`. |
| `leak_night_end` | `"05:00"` | Exclusive local end time, strict `HH:MM`; must differ from the start. A start later than the end crosses midnight. |
| `leak_night_min_pulses` | `1` | Minimum pulses per observed night interval, integer 1–65535. |

## Rules and recovery

**Continuous flow:** every observed hourly interval in the last N hours must have
more than zero pulses, and at least 80% of those hours must be observed. With the
default 24-hour horizon this needs at least 20 observations. Missing hours count
as neither flow nor zero. Once triggered, this reason stays active through gaps
and clears when a new observed zero-flow interval arrives. A later qualifying
run can trigger it again. Elapsed hours are measured in UTC, including across DST.

**Night flow:** every observed interval ending inside the local night window must
have at least `leak_night_min_pulses`, with at least three observed intervals.
The rule decides only when the window is complete, so the hint arrives at the
end of the window. With at least three observations, all must meet the threshold
to activate this reason; any below the threshold clears it. Daytime zeroes and
nights with fewer than three observations leave the previous state unchanged.
The end time is exclusive; for example, an interval
ending at exactly 05:00 is outside the default window. Midnight-crossing windows
belong to their start date. Repeated DST hours are distinct observations, while
skipped hours are not invented. An ambiguous end time uses its later occurrence.

Either reason makes the binary sensor ON. If both are active, the continuous-flow
reason is displayed first; clearing it can leave `night flow` active. Rule state
survives restarts. Changing rule options or timezone recomputes it from the
existing bounded history.

## Home Assistant and MQTT

Each configured meter has `binary_sensor.taggle_<id>_possible_leak`, with device
class `problem`. MQTT discovery uses `default_entity_id`, so existing entity
renames are preserved. Availability follows the meter's usage sensors: receiver
online, a valid frame within three hours, and decoded counts available. An OFF
sensor means no qualifying hint, not proof that the plumbing is leak-free.

With the default MQTT prefix, `taggle/<id>/leak` carries `state` (`ON` or `OFF`)
and these attributes. It is retained and republished after reconnects; rule
checkpoint fields stay private in the store.

| Attribute | Meaning |
| --- | --- |
| `reason` | `continuous flow for 24 h` (or the configured N), `night flow`, or null when OFF. |
| `hours_with_flow_last_24h` | Observed intervals with positive pulses in the preceding 24 elapsed hours. |
| `longest_zero_run_hours` | Longest consecutive observed zero run in those 24 hours; gaps break the run. |
| `night_pulses` | Sum of pulses in the most recent observed night window, including a window still in progress. Zero when no night intervals remain in history. |
| `observed_hours` | Number of observed intervals in the preceding 24 elapsed hours. |
| `last_evaluated` | ISO-8601 UTC evaluation time. Periodic refreshes leave the radio `last_seen` unchanged. |

## Dashboard card

Device-based cards discover the binary sensor through the entity registry,
including renamed entities. For an explicit entity mapping, append:

```yaml
entities:
  # Keep your existing mappings, then add your own meter's actual entity ID:
  possible_leak: binary_sensor.taggle_123456_possible_leak
```

For a list of entity IDs, add that binary sensor to the list. When its Home
Assistant state is `on`, a small **Possible leak** badge shows the reason. OFF,
unknown, unavailable, and missing sensors show no badge.

See the wiki [Entities reference](https://github.com/Spicynostalgia/ha-taggle/wiki/Entities-Reference)
and [Configuration reference](https://github.com/Spicynostalgia/ha-taggle/wiki/Configuration-Reference)
for the surrounding receiver settings and entities.
