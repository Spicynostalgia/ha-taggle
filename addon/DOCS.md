# Taggle water meter add-on

Requires an RTL-SDR, an antenna for 915–928 MHz, and the Home Assistant MQTT integration with a Supervisor-discoverable MQTT broker. Supports amd64 and aarch64. The build includes the RTL-SDR Blog driver for Blog V4 support.

[Wiki](https://github.com/Spicynostalgia/ha-taggle/wiki) — beginner guides live here too.

## Install

The receiver add-on needs **Home Assistant OS or Supervised**. **Home Assistant Container/Core** users should use [Standalone Docker](https://github.com/Spicynostalgia/ha-taggle#standalone-docker). A running **MQTT broker** and the Home Assistant MQTT integration are prerequisites; use Mosquitto below if you need a broker, then configure the discovered MQTT integration under **Settings → Devices & services**.

[![Open your Home Assistant instance and show the dashboard of an add-on.](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=core_mosquitto)

Open the add-on repository below, add it, then open **Taggle water meter**: **Install → set `meter_ids` → Start**. Connect the SDR and antenna; leave `litres_per_count: []` until calibrated and set your timezone. Supervisor supplies MQTT credentials. See Setup below for details.

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FSpicynostalgia%2Fha-taggle)

The optional dashboard card is installed separately through HACS. With HACS already installed, open its repository below, download the card and reload your browser. See the [dashboard card guide](https://github.com/Spicynostalgia/ha-taggle#7-add-the-dashboard-card) for configuration.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Spicynostalgia&repository=ha-taggle&category=plugin)

## Tested hardware

**Exactly one transmitter has been verified so far:** Gladstone Regional Council, QLD, with an **RTL-SDR Blog V4**, **18-byte clear frames**, **hourly** updates and **922.2 MHz SDR centre**. The automated tests use generated signals; other deployments/models are not field-verified.

The tested unit is a white cylindrical “baton” pulse transmitter hose-clamped to the supply pipe, with a thin cable to a pulse/Hall sensor on a V100-style mechanical meter (flip lid, black kL and red litre digits). The label has “taggle”, a barcode and an ID, **no model number**. SP-series / ADC-1 family identification is plausible but **unconfirmed**.

See the [tested unit and identification guide](https://github.com/Spicynostalgia/ha-taggle#tested-hardware). Please [report other councils/models](https://github.com/Spicynostalgia/ha-taggle/issues) with whether usage worked, a label photo with the ID and identifying barcode blurred, frame length and SNR. Other Taggle generations may use different channels or encryption; NB-IoT/cellular models cannot be received by this project.

## Beginner guide

New to SDR? Follow the [beginner walkthrough](https://github.com/Spicynostalgia/ha-taggle#getting-started-beginner-guide) for hardware, safe meter identification, reception checks, dashboard setup and calibration.

![Illustration: receive-only path from the meter box through SDR and MQTT to Home Assistant](https://raw.githubusercontent.com/Spicynostalgia/ha-taggle/main/docs/images/setup-diagram.svg)

*Illustration: the receiver setup. The broker can share the HA host; Energy requires calibration.*

![Taggle dashboard card with fictional calibrated usage](https://raw.githubusercontent.com/Spicynostalgia/ha-taggle/main/docs/images/card-light.png)

*Dashboard preview with synthetic data and fictional IDs; no default calibration is assumed.*

## Setup

Enter your own decimal transmitter ID in `meter_ids`. The transmitter label is usually marked `ID:xxxxxx`. Do not substitute the mechanical register serial. Every sample ID in this project is fictional.

Start with `litres_per_count: []`: counts have no assumed water-volume unit. Set your IANA timezone to match Home Assistant so daily totals use the intended local date. `device` accepts an RTL index or serial, `frequency` defaults to 922200000 Hz, and `gain` defaults to 40 dB. The sample rate is fixed at 2400000.

Supervisor supplies MQTT host, port, username and password automatically via the `mqtt:need` service. The startup script reads `/data/options.json`, writes a private runtime configuration under `/run`, and executes the receiver. It never prints broker credentials. USB plug-and-play access is requested with `usb: true`; another driver or SDR app must not hold the receiver.

## Scan

Set `scan_minutes` to 65 and start. Watch the log for IDs and SNR. A scan allows an empty meter list, prints counts only for configured IDs, and writes no usage state/logs or MQTT messages. It exits when the duration elapses. Set `scan_minutes` back to zero, configure your ID and restart for normal operation.

## Entities and data

One MQTT device is created per configured meter. Supported clear frames expose hourly usage, today's partial observed total and a cumulative observed count, plus SNR, signal level and last seen. Encrypted frames expose diagnostics only. Adding `litres_per_count` entries (`meter_id` and positive `value`) enables litre entities, including a persistent `total_increasing` water entity for Energy.

Discovery uses `default_entity_id`: meter IDs default to `sensor.taggle_<id>_<key>` (for example `sensor.taggle_123456_today` and `sensor.taggle_123456_total_litres`), and aggregate IDs to `sensor.taggle_neighbourhood_<key>`. Existing registry IDs and user renames are preserved; collisions may add a suffix. The card’s device mode uses stable registry unique IDs, including for older name-derived IDs.

`neighbourhood` defaults to true. Other IDs never enter normal logs, JSONL, state or MQTT: neighbour counter tracking uses HMAC-SHA256 keys (16 hex characters) with a random 32-byte install salt in `/data/receiver/neighbourhood.salt` (0600). Only a **Taggle neighbourhood** device with aggregate sensors is published, with no per-neighbour entities. Your configured meters are excluded. Neighbours not heard for more than seven days are pruned. Set `neighbourhood: false` and restart to delete neighbour state and salt and remove retained neighbourhood discovery/state.

`neighbourhood_min_meters` defaults to 3 and cannot weaken the privacy floor below three. Each cohort's entities are unknown below the floor: meters heard within 24 h (including encrypted); clear meters qualifying today; or clear meters with a recent interval. Today requires at least six observed intervals ending on the local date and at least 75% of elapsed local clock hours observed. Missing intervals are never scaled or estimated. The last-hour average uses each clear neighbour's latest interval ending within two hours. Recomputed every minute; encrypted meters never contribute to usage.

The sensors are `neighbourhood_meters_heard`, `neighbourhood_meters_counted`, `neighbourhood_average_today`, `neighbourhood_median_today` and `neighbourhood_average_last_hour` (default entity IDs start `sensor.taggle_`). Each configured meter also gets `vs_neighbourhood_today`, a percentage of the neighbourhood average (100 means equal), unknown when either value is missing, units differ or the average is zero. Average/median sensors use measurement statistics, not cumulative Energy totals. The card automatically shows average, median, qualifying homes and the comparison; renamed sensors can be mapped with `neighbourhood: {average_today: ..., median_today: ..., meters_counted: ...}`.

**Neighbours' litres per count is unknown.** Optionally set `neighbourhood_litres_per_count` to an assumed positive pulse value. When omitted, the first ID in `meter_ids` supplies its calibrated factor, or the aggregate uses raw pulses. Same council/model usually means the same pulse value, but this is unverified. Reception is biased toward strong nearby signals; partial-day usage stays partial. The median is more robust to a leaking neighbour than the average. See the root README's [Neighbourhood comparison](https://github.com/Spicynostalgia/ha-taggle#neighbourhood-comparison) for details.

`log_all_meters` remains false by default. Explicitly enabling it allows other IDs to enter JSONL logs if logging is also enabled; it creates no per-neighbour MQTT entities. Scan output is unchanged and can print heard IDs.

State is stored under `/data/receiver` and survives add-on restarts and upgrades. Include app data in backups. `jsonl_logging` is optional and defaults to false. Enabled daily JSONL logs require your own retention management. Do not publish your options, logs or state.

New receiver data directories use mode 0700; JSONL logs, state and the neighbourhood salt use 0600.

The standalone Python package and root README contain the full protocol, calibration, card configuration and troubleshooting guidance. The add-on's package files are the same source installed by the root Python project.

When replaying a recording with the standalone CLI, availability and the final today/neighbourhood refresh use the current wall clock, so old recordings can show unavailable sensors and zero today. Standalone Python supports 3.11–3.13; on Debian/Ubuntu install `python3-venv` before creating a virtual environment.

## Troubleshooting

- No frames: confirm a suitable antenna, wait over an hour, verify SDR USB access and reduce strong-signal overload by lowering gain.
- USB errors: stop competing SDR software, check power/cabling and whether the host DVB driver has claimed the device. The receiver retries a disconnected producer after two seconds.
- No entities: confirm Home Assistant's MQTT integration uses the same broker and scan mode is off. Discovery is retained and resent when Home Assistant announces it is online.
- Usage unavailable: 24-byte encrypted transmitters provide no counts, and meters expire after three hours without a valid frame.
- Partial totals: only recovered hourly intervals count. This receiver cannot reconstruct arbitrarily long gaps.

Unofficial; not affiliated with Taggle Systems or any utility. Receive-only, for your own meter. Respect local radio and privacy laws. Encrypted payloads are not and will not be attacked.
