# Taggle water meter add-on

Receive hourly pulse updates from a supported Taggle transmitter in Home Assistant. You need an RTL-SDR USB receiver, an antenna for 915–928 MHz and MQTT. Mosquitto can provide the broker if you do not have one.

**Only one transmitter has been verified:** Gladstone, QLD, with an RTL-SDR Blog V4. Other models and areas are unverified. This add-on supports amd64/aarch64 and includes the Blog driver for V4 support. The historical Docker hardware test used receiver 0.2.1; these instructions describe **0.3.0**.

> [!IMPORTANT]
> The transmitter sends a pulse counter, not your dial reading. Its starting offset and litres per pulse are both unknown. Guided calibration in **0.3.0** uses a one-hour routine: read just after a transmission, use 20–50 L (reuse it), then read after the next transmission to establish both; follow Calibration status if another reading is needed. Check the estimate against your physical dial. This is experimental, not billing-grade measurement.

## Install

Use **Home Assistant OS** with an administrator account. Open `http://homeassistant.local:8123` (some new installs serve on port 80: omit `:8123`). An add-on is a program managed by HA OS; newer menus call it an app. Existing Supervised installations may also run it, but [upstream support ended after 2025.12](https://www.home-assistant.io/blog/2025/05/22/deprecating-core-and-supervised-installation-methods-and-32-bit-systems/). Container users should follow [Standalone Docker](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-with-Docker).

[![Open Mosquitto broker](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_mosquitto)

1. In **Settings → Apps (Add-ons) → Store / Install app**, install **Mosquitto broker** if needed, enable **Start on boot**, and Start. Configure the discovered **MQTT** integration under **Settings → Devices & services**. If absent, choose **Add integration → MQTT** and follow the broker's Documentation tab.
2. Add the repository using the button below, or the Store's **⋮ → Repositories** with `https://github.com/Spicynostalgia/ha-taggle`. Refresh the Store, install **Taggle water meter**, then connect the USB receiver and antenna.
3. Follow **Setup** below, Save, enable **Start on boot**, Start, and open **Log/Logs**. Supervisor supplies MQTT credentials automatically; no broker password belongs in these add-on options.

[![Add the Taggle add-on repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FSpicynostalgia%2Fha-taggle)

The custom card is optional; standard HA sensor cards work too. For a browser-only installation without HACS, follow the [README card steps](https://github.com/Spicynostalgia/ha-taggle/blob/main/README.md#add-the-dashboard-card). HACS is a community tool for cards and integrations, separate from the add-on Store. Complete its [prerequisites](https://hacs.dev/docs/use/download/prerequisites/), [download](https://hacs.dev/docs/use/download/download/) and [configuration](https://hacs.dev/docs/use/configuration/basic/) before using the button:

[![Open the card in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Spicynostalgia&repository=ha-taggle&category=plugin)

## Tested hardware

The one verified setup used **18-byte clear frames**, **hourly** updates and **922.2 MHz SDR centre**. Automated tests use generated signals; they do not field-verify other deployments.

The tested meter is an **Elster (Honeywell) V100**, owner-confirmed. Elster’s [V100 PSM-T specification](https://cdn.shopify.com/s/files/1/0556/0283/9744/files/V100_PSM_T_SML001_SpecSheet.pdf) lists **5 L/pulse** for the **5 black + 3 red** counter and **0.5 L/pulse** for the **4×4** counter. The tested meter’s readings match **5 L/pulse**; **still calibrate yours**. The radio counter has an arbitrary starting offset, so multiplying it by 5 does not reconstruct your dial reading.

The transmitter is a white cable-connected cylinder. Its exact model is unconfirmed; appearance alone does not establish compatibility. **NB-IoT/cellular models cannot be received.** Other Taggle generations may use other channels or encryption. See the [tested setup and identification guide](https://github.com/Spicynostalgia/ha-taggle/wiki/Tested-Hardware).

Working or stuck? [Report your result](https://github.com/Spicynostalgia/ha-taggle/issues/new/choose) with the version, installation method, council/utility, receiver model and whether usage, ID only, or nothing was heard. Frame length and SNR are optional; **unknown is fine**. Normal logs and scans do not show exact frame length. Replace IDs with fictional **123456**, cover IDs/barcodes in photos, and omit private configuration, credentials and recordings.

![Illustration: receive-only path from the meter box through SDR and MQTT to Home Assistant](https://raw.githubusercontent.com/Spicynostalgia/ha-taggle/main/docs/images/setup-diagram.svg)

*Illustration: the USB receiver listens; MQTT carries observations to Home Assistant. Energy needs calibration.*

## Setup

Open the add-on's **Configuration** tab. Add your decimal transmitter ID to the `meter_ids` list in the form. In **⋮ → Edit in YAML**, change the existing entry to `meter_ids: [123456]`, substituting your own ID. Keep other options. This is **add-on configuration**, not Home Assistant's `configuration.yaml` or Docker JSON. The mechanical meter serial is not the transmitter ID.

Leave `litres_per_count: []` for guided calibration. Match `timezone` to Home Assistant's named zone, such as `Australia/Brisbane`, `Australia/Sydney`, `Australia/Adelaide` or `Australia/Perth`; use your own region. It controls daily totals and local photo times; scans use UTC. **Save** before starting/restarting **Taggle water meter**. If the label is unreadable, leave `meter_ids: []` and use Scan below; normal reception needs a confirmed ID.

**Before first Start:** neighbourhood comparison is **on by default**. It publishes group statistics, not individual neighbours' identities/usage. To disable collection, set `neighbourhood: false`, Save, then start/restart the add-on. Hiding the card row only hides the display.

Check that the add-on stays running, the USB receiver is detected and `Reading samples in async mode...` appears. In normal mode, confirm `MQTT connected`. Resolve startup errors now; once healthy, allow a full **65 minutes** for a transmission opportunity. Reception is not guaranteed. Receiver log lines include an ISO local timestamp and UTC offset from the process/container timezone (`TZ`); scan JSON uses UTC frame times. Every 15 minutes a normal-mode heartbeat counts frames and distinct other meters without printing neighbour IDs; it does not prove your own transmitter was heard.

MQTT discovery announces the configured Taggle devices and enabled neighbourhood device immediately on broker connection. Unknown/unavailable initial values are expected; missing devices call for checking configuration/MQTT, rather than waiting for the radio. Open **Settings → Devices & services → MQTT → devices → Taggle [your ID]**. Look under **Diagnostics** for Last seen, SNR and signal level.

## Guided calibration

Manual dial readings are the main route in **0.3.0**. No utility account, maths or restart is needed.

1. **Just after a transmission**, read the dial within **10 minutes**, before anyone uses water. The card shows **Read now** with minutes remaining; **Good time to read the dial** turns on. Choose **m³, kL or L** to match the face (1 m³ = 1 kL = 1,000 L), type the full reading, and save promptly.
2. **Use some water during the hour**, for example fill buckets or run a shower, about **20–50 L**. Reuse the water. This is practical guidance, not a minimum-usage gate.
3. **Just after the NEXT transmission** (normally about one hour later), read within 10 minutes again, before further water use. Save the second reading and follow **Calibration status**. When exactly one standard pulse size fits, calibration supplies litres automatically. If multiple sizes fit, status names them and asks for another reading.

The transmit minute can drift (about **13 seconds earlier per hour** in the overnight hardware test). **Next transmission expected ≈ HH:MM** follows observed timing; use it and the actual **Good time to read the dial** window rather than a fixed minute each hour.

On the MQTT device page use **Dial unit (m³ = kL, or L)**, then the single **Dial reading (e.g. 1597.765 or 1597.765 18:00)** box. Fresh: `1597.765` or `1597,765`. Photo: `1597.765 18:00`, `1597.765 1800`, `1597.765 at 6:00`, `1597.765@18:00`, or `1597.765 2026-11-02T18:00:00+10:00`. The reading and time are submitted together to `taggle/<id>/reading/set`; there is no pending photo-time setting. Clock times use the receiver’s timezone and mean yesterday if ahead of now. JSON entries remain supported.

Outside the window is less precise; a third reading may be needed. Return to the one-hour routine above for the next reading. **Read your dial now** (`binary_sensor.taggle_123456_read_dial_now`, displayed as **Good time to read the dial**) is on for ten minutes after each configured-meter frame; attributes give `since`, `until`, and `next_transmission`. Status readings expose `exact` only when the window and a no-pulse bracket agree. **Delete all dial readings** is under **Configuration**; it clears entered readings and automatic calibration, keeping units, usage totals and pins. Old unknown saved options are ignored with a warning.

Check later dial readings against the estimate. If an entry is wrong, [delete that reading or review reset consequences](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/CALIBRATION.md#correct-or-reset-readings) before using **Delete all dial readings** under **Configuration**. Reset clears readings and automatic calibration, preserving observed usage totals and configuration pins.

Already configured a manual `litres_per_count`? It pins litres per pulse: guided readings check it but cannot replace it. For automatic selection, clear `meter_reading_offset: []` if present, then `litres_per_count: []`, Save and restart **Taggle water meter** once. Guided reading submissions need no restart.

For an example phone notification when **Read your dial now** turns on, see the calibration guide below.

Photo times, statuses, options, correction and the advanced manual/utility routes: [Calibration guide](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/CALIBRATION.md).

## Possible leak alert

Enabled by default for configured meters only, never neighbours. Each gets a `problem` binary sensor, `binary_sensor.taggle_<id>_possible_leak`, available whenever its usage sensors are available. The dashboard card can show a small **Possible leak** badge with the reason; add `possible_leak` to explicit card entity mappings or lists. Device-based cards find it automatically.

| Option | Default | Accepted values |
| --- | --- | --- |
| `leak_detection` | `true` | Boolean; false removes possible-leak discovery. |
| `leak_continuous_hours` | `24` | Integer 1–168 hours; all observed intervals must have positive pulses with at least 80% coverage. A new observed zero clears this reason. |
| `leak_night_start` | `"01:00"` | Inclusive local `HH:MM`, using `timezone`. |
| `leak_night_end` | `"05:00"` | Exclusive local `HH:MM`, different from start; supports crossing midnight. |
| `leak_night_min_pulses` | `1` | Integer 1–65535; evaluated only at the end of the night window. With at least three observations, all must meet this threshold to activate the night hint; any below it clears the night-flow reason. Fewer observations leave its state unchanged. |

**A hint, not an alarm:** the receiver sees hourly totals only. A dripping tap below one pulse per hour is invisible. Irrigation schedules can trigger night flow; adjust the night window to suit your household. Missing intervals are neither flow nor zero and cannot establish recovery. Calibration is not required. See the [full rules, attributes and card mapping](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/LEAK-DETECTION.md) and wiki [Entities reference](https://github.com/Spicynostalgia/ha-taggle/wiki/Entities-Reference).

## Scan

Change modes by restarting this same add-on; do not start a second receiver against the USB device. Set `scan_minutes: 65`, **Save**, then **Start/Restart Taggle water meter**. An empty `meter_ids: []` is allowed for scanning. Watch Log/Logs for decoded IDs; silence can mean no frames yet. A scan covers an expected hourly opportunity, not guaranteed reception.

Scans create no MQTT messages, usage state or JSONL logs and have no normal heartbeat. They exit after the requested duration. Afterwards confirm your ID using the label, a repeated household water-use check or your utility. Configure only your confirmed ID, restore **`scan_minutes: 0`**, Save and Start the add-on in normal mode. Never leave fictional `123456` configured. Do not add `scan_minutes` to standalone JSON; Docker/Python use `--scan` instead.

Fictional unconfigured scan line:

```json
{"time":"2026-01-01T12:15:00+00:00","meter_id":123456,"snr_median_db":30.1,"signal_level_dbfs":-40.9}
```

`time` is sample-derived UTC frame time. Only configured clear meters also include `"counts": [120, 110, 104]`; missing counts for an unconfigured ID do not prove encryption. Keep scan output private. [Exact scan schema](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/PROTOCOL.md#scan-output).

## Entities and data

| Value | Meaning |
| --- | --- |
| Raw radio counter | Wrapping 16-bit pulses with an arbitrary starting offset; not the dial. |
| `meter_count` | ha-taggle's cumulative recovered hourly pulses; also not the dial. |
| **Meter reading** | Calibrated estimate of the absolute dial, in litres. Choose this for **Settings → Dashboards → Energy → Water** once available. |
| `total_litres` | Observed cumulative usage: each newly recovered interval uses the litres per pulse active on first processing. Earlier stored intervals are not recalculated; recent earlier intervals may still arrive later. |

Selecting Meter reading starts statistics from a baseline; it does not import lifetime consumption or recreate historical hourly data. Allow an hour or two for Energy statistics. With only a manual factor and no absolute reading, Total litres can be used instead. Select one source per supply. Review statistics after calibration corrections/reset or source changes; continuity is not guaranteed across a changed absolute estimate. Hourly/daily litre displays use the current factor. Only unrecovered intervals are omitted; a later frame can recover one missed transmission.

Supported clear frames expose usage and diagnostics; confirmed encrypted frames provide diagnostics only. Usage can also disappear temporarily after a counter/sequence discontinuity. Discovery preserves existing entity IDs and renames. On a device, open sensor → settings → **Entity ID** before copying it into card YAML; the friendly name and transmitter ID are different things. Device-mode cards use the HA registry ID and find calibration/litre/leak entities automatically. See [Entities reference](https://github.com/Spicynostalgia/ha-taggle/wiki/Entities-Reference) and [card setup](https://github.com/Spicynostalgia/ha-taggle/blob/main/README.md#add-the-dashboard-card).

### Neighbourhood comparison and privacy

**Today uses each interval’s end date in the configured local timezone.** The interval **23:39–00:39** counts towards the **new day**, for your meter and the neighbourhood.

Neighbourhood comparison is on by default. Each cohort stays unknown below **three qualifying meters**; hearing three IDs alone does not qualify today's usage. Today also requires six observed intervals and at least 75% of elapsed local clock hours. The add-on accepts `neighbourhood_min_meters` of 3 or greater; standalone clamps lower integers to 3. After local midnight, today’s average, median, counted meters and per-meter comparison stay **unknown until at least three neighbours each have six new-day intervals and sufficient coverage again**. This can take roughly **five hours** (00:00–05:05 in the overnight hardware test); actual timing depends on transmissions and reception. It is expected each morning. Missing intervals are not estimated. Encrypted neighbours contribute only to the heard count.

Neighbours' litres per pulse are unknown. Unless `neighbourhood_litres_per_count` is set, aggregates use the first configured meter's calibrated value or raw pulses. Your calibration does not calibrate neighbours. This is a rough, reception-biased group comparison, not a household efficiency ranking. Aggregate measurements are not Energy totals.

The card hides percentages when displayed units differ. **Receiver limitation:** when the first meter is uncalibrated and a later configured meter is calibrated, MQTT can still emit a raw-pulse `vs_neighbourhood_today` percentage for that later meter. Do not interpret it as a litres comparison.

With default logging, neighbour IDs are absent from normal logs, JSONL, state and MQTT. Private neighbour state uses installation-specific opaque HMAC keys, and only group statistics reach MQTT; your own configured meters are excluded. **Exceptions:** scans print heard IDs, and enabling both `log_all_meters` and `jsonl_logging` writes them into private JSONL summaries. Disabling `neighbourhood`, then saving/restarting the receiver, removes neighbour state/salt and retained aggregate discovery/state. Hiding the card row alone does not stop collection. [Cohorts, assumptions and controls](https://github.com/Spicynostalgia/ha-taggle/wiki/Neighbourhood-Comparison).

### Backups and reference details

Private state lives under `/data/receiver` and survives add-on restarts/upgrades. **Include the add-on's data in HA OS backups before updating**: dial readings and the solution are in state, not just options. Do not delete state or reinstall to fix reception. New data directories use 0700; JSONL logs, state and neighbourhood salt use 0600. Optional `jsonl_logging` is off by default; enabled logs need your own retention management. Keep options, logs and state private.

Find the receiver version on the add-on Info tab or MQTT device information. Update the receiver and optional card together to **0.3.0**; replacing a manual card's file also needs browser/cache reload. [Backup and update steps](https://github.com/Spicynostalgia/ha-taggle/blob/main/README.md#back-up-and-update).

For all option names/defaults see [Configuration reference](https://github.com/Spicynostalgia/ha-taggle/wiki/Configuration-Reference); for decoding see the [protocol specification](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/PROTOCOL.md). The standalone Python package uses the same receiver source and supports Python 3.11–3.13. Its replay availability and final daily refresh use the current wall clock, so old recordings can show unavailable sensors and zero today.

## Troubleshooting

- **Startup or USB failure:** resolve errors immediately. Stop competing SDR software; check app USB access, power/cabling and VM passthrough if used. The receiver retries after two seconds, backs off to 60 seconds while the SDR remains unavailable, and repeats its USB/passthrough hint at most every ten minutes. Linux DVB driver commands are host-specific, not ordinary HA OS setup.
- **No frames after healthy startup:** check antenna, placement and host noise. After changing gain or other options, Save and Restart Taggle water meter; compare reception over 65 minutes. Another channel or unsupported transmitter remains possible.
- **No devices:** check configured IDs, normal mode (`scan_minutes: 0`), the same broker in HA, MQTT connection and discovery. Discovery happens on broker connection before a radio frame.
- **Usage unavailable:** a new device can wait for its first frame. Previously seen meters expire after three hours. Encryption or sequence discontinuity can leave diagnostics updating without usage; unavailable alone does not diagnose encryption.
- **Partial totals:** only recovered hourly intervals count. A later frame can recover a single missed transmission; long gaps can remain incomplete.

A new custom card uses a neutral “Waiting for first reading (can take up to an hour)” message. Previously observed meters keep warnings when reception fails. [Troubleshooting guide](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting).

Unofficial; not affiliated with Taggle Systems or any utility. Receive-only, for your own meter. Respect local radio and privacy laws. Encrypted payloads are not and will not be attacked.
