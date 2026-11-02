# Taggle water meter → Home Assistant

Receive your own Taggle-equipped water meter with an RTL-SDR. This project decodes supported hourly transmissions and publishes water usage and signal diagnostics through Home Assistant MQTT discovery. It runs as a Home Assistant add-on, a standalone Docker container, or a Python CLI.

**0.1.0 is experimental.** The test suite uses generated signals, not recordings. A fresh installation still needs confirmation against your transmitter and meter register. This is hourly usage, not an instantaneous flow or leak alarm.

<img src="docs/images/card-light.png" alt="Taggle card in a light theme, showing fictional calibrated water usage and its expanded 48-hour history" width="552">

*Dashboard preview using synthetic data and fictional meter IDs. The example calibration is not a recommended scale for your meter.*

**What you get**

- Hourly usage in raw pulses for supported clear-format transmitters, plus signal diagnostics.
- Litres and a water total for Home Assistant Energy after you calibrate against the register.
- A dashboard card with 48-hour history, visible gaps, light/dark themes and multiple meters.
- Home Assistant add-on, Docker and Python installation options; reception stays local.

## Getting started (beginner guide)

An SDR (software-defined radio) is a USB radio receiver. It listens to your meter; it does not connect to or modify the meter. MQTT carries the decoded readings from the receiver to Home Assistant.

![Illustration: meter box sends hourly radio to an antenna and RTL-SDR, then the HA host, MQTT broker and dashboard](docs/images/setup-diagram.svg)

*Illustration: the receive-only setup. The MQTT broker can run on the same host. Energy needs calibrated litres.*

### 1. Check you have a Taggle meter

- [ ] Ask your council/water utility, or search its website for **smart water meter**, **Taggle** or **digital meter**. [Several Australian councils and utilities use Taggle](https://taggle.com/case-studies/), and it is also used elsewhere; a digital meter alone does not confirm compatibility.
- [ ] Look in your meter box for a Taggle transmitter or label. This experimental receiver targets a known channel near 922 MHz; it does not support every smart meter or every Taggle deployment. See [transmitter support](#hardware-and-transmitter-support) before buying hardware.

### 2. Open your meter box safely

- [ ] Find the usually in-ground rectangular box near the front boundary or footpath. Wear gloves. Lift the lid carefully with a screwdriver at the lifting slot; don't stand on the lid or force it open.
- [ ] In Australia, check for spiders (including redbacks), snakes, ants and wasps. If you cannot inspect it safely, close it and ask the utility for help.
- [ ] **Do NOT remove, open, unplug or move the transmitter or meter. It belongs to the utility.** Just look and photograph, then replace the box lid.

### 3. Identify the transmitter and its ID

![Illustration: open in-ground meter box with callouts for the register, meter serial and transmitter ID 123456](docs/images/meter-box.svg)

*Illustration: a typical arrangement, not a photo. Your box and transmitter may look different.*

![Illustration: plain transmitter label with ID 123456 circled and a separate serial marked not this one](docs/images/transmitter-label.svg)

*Illustration: simplified label with fictional numbers; no real product logo is reproduced.*

- [ ] Take a phone photo of the **transmitter label**. Its decimal **ID** (often about six digits, e.g. fictional `123456`) is different from the mechanical meter's serial number or a separate barcode serial.
- [ ] Photograph the **register reading**, including its units (litres or m³), and keep the timestamp. This is useful later for calibration; it is not the radio counter.
- [ ] If the label is unreadable, use the scan and tap test in [step 6](#6-confirm-youre-receiving-your-meter). Ask the utility if you still cannot identify it confidently.

### 4. Get the hardware

- [ ] **RTL-SDR USB receiver:** the RTL-SDR Blog V4 is a recommended, driver-supported choice if you own one or find genuine remaining stock. Budget roughly **AUD 60** for a dongle as a starting estimate; kits, shipping and stock vary. [V4 production has ended](https://www.rtl-sdr.com/rtl-sdr-blog-v4-end-of-line/); use the [manufacturer's reseller list](https://www.rtl-sdr.com/buy-rtl-sdr-dvb-t-dongles/) to check availability. The Blog V3 is another option.
- [ ] **915–928 MHz antenna:** a quarter-wave whip is about **8 cm** at 922 MHz. With the stock telescopic dipole kit, use the short elements at about **8 cm per side**. See the [manufacturer's antenna guide](https://www.rtl-sdr.com/using-our-new-dipole-antenna-kit/).
- [ ] **USB extension cable:** move the dongle away from computer noise and closer to a window facing the meter.
- [ ] **Host:** a Pi 4/5, mini PC, or NAS with Docker and SDR USB access. Use the machine running HA if suitable; this project provides amd64/aarch64 container images. A VM needs USB passthrough.

### 5. Install

For **Home Assistant OS**, use the add-on (called an *app* in newer HA menus). Non-HAOS users: follow [Standalone Docker](#standalone-docker), then return to step 6. On Docker/Linux, a DVB TV kernel driver can claim the dongle; release/blacklist that driver on the host if it causes “device busy”.

1. [ ] In **Settings → Apps (Add-ons) → Store**, install and start **Mosquitto broker**, unless you already have a Supervisor-discoverable MQTT broker. Under **Settings → Devices & services**, configure the discovered **MQTT** integration. See [HA's MQTT setup](https://www.home-assistant.io/integrations/mqtt/).
2. [ ] In the Store's **⋮ → Repositories**, add `https://github.com/Spicynostalgia/ha-taggle` and click **Add**. See [HA's app repository instructions](https://www.home-assistant.io/common-tasks/os/#installing-a-third-party-app-repository) if your menu differs.
3. [ ] Refresh the Store, open **Taggle water meter**, and click **Install**. Connect the SDR and antenna.
4. [ ] Open the add-on's **Configuration** tab. Set `meter_ids` to your own decimal transmitter ID, leave `litres_per_count: []`, and set your timezone (for example `Australia/Brisbane`). Save. The add-on gets MQTT credentials from Supervisor; you do not paste them into these options.
5. [ ] Click **Start**, then open **Logs**. After a supported frame arrives, look under **Settings → Devices & services → MQTT** for the meter device. If you need to find the ID first, leave `meter_ids: []` and run the scan below.

### 6. Confirm you're receiving your meter

- [ ] Set **`scan_minutes: 65`**, save and restart the add-on. Watch **Logs** and wait the full 65 minutes: a transmitter may send only **once per hour**. Docker/CLI users can use [the scan commands](#find-your-meter-id). Scan mode publishes no MQTT entities and saves no usage state.
- [ ] Look for lines like this **synthetic example** (all numbers are fictional):

```json
{"meter_id": 123456, "snr_median_db": 12.4, "signal_level_dbfs": -43.2}
```

`snr_median_db` is a **despread correlation SNR estimate**, not the raw antenna SNR. Higher is better when comparing antenna positions, but there is **no field-validated “good” cutoff** in this release. The [synthetic receiver tests](tests/test_receiver.py) check that decoded test frames exceed 5 dB; this is a test assertion, not a required reception threshold. Repeated valid hourly frames are the useful check. Scan output includes `counts` only for IDs already in `meter_ids` and only for clear-format frames; missing counts in an unconfigured scan do not establish encryption.

- [ ] For the **tap test**, configure your ID (or a plausible candidate from an unreadable label), set `scan_minutes: 0`, save and restart. Wait for a normal reading and note the time and `last_hour`. With nothing else using water, fill a **10 L bucket twice**, note the time, then check that `last_hour` increases at the next transmission. Counts are still pulses, so do not expect the number `20`. Radio interval boundaries can split the draw; check the following update too if needed. Reuse the water.
- [ ] If identifying a candidate, repeat the timed test to confirm its response matches your own meter. A strong signal alone does not identify your meter; do not keep someone else's ID configured. Encrypted transmitters cannot support a usage tap test; ask the utility to confirm the ID instead.
- [ ] If nothing appears, move the antenna closer to the meter or a facing window, try a higher position and a USB extension, then try `gain: 40` → `49`. Higher gain can overload the receiver; lower it again if reception worsens. Wait another full scan after each change. This receiver does not search every Taggle channel.
- [ ] Finish by setting **`scan_minutes: 0`**, configuring only your meter ID(s), saving and restarting for normal MQTT operation.

### 7. Add the dashboard card

1. [ ] If needed, [install HACS](https://www.hacs.dev/docs/use/download/download/) (the community store, separate from the add-on Store).
2. [ ] Open **HACS → ⋮ → Custom repositories**, enter `https://github.com/Spicynostalgia/ha-taggle`, select **Dashboard**, and add it. Search for **ha-taggle**, open it and **Download**. Reload your browser when prompted. See [HACS custom repositories](https://www.hacs.dev/docs/faq/custom_repositories/).
3. [ ] In your HA dashboard, choose **Edit dashboard → Add card → Manual** and paste the example below. Replace the fictional ID with yours; check the actual entity IDs under the MQTT device if HA renamed them. Save.

```yaml
type: custom:taggle-card
title: Water usage
entities:
  last_hour: sensor.taggle_123456_last_hour
  today: sensor.taggle_123456_today
  meter_count: sensor.taggle_123456_meter_count
  last_seen: sensor.taggle_123456_last_seen
  snr: sensor.taggle_123456_snr
  signal_level: sensor.taggle_123456_signal_level
```

<p>
  <img src="docs/images/card-dark.png" alt="Dark theme card with fictional calibrated usage and expanded history" width="330">
  <img src="docs/images/card-mobile.png" alt="Mobile width card with fictional calibrated usage and expanded history" width="260">
</p>

*Synthetic dashboard previews: dark theme and mobile width. The card starts in raw pulses until calibrated; these previews show litres.*

For manual resource installation, calibrated entity mappings and device selection, see [Dashboard card reference](#dashboard-card). Multiple meters can share one card:

<img src="docs/images/card-multi.png" alt="Two-meter card showing fictional House and Granny flat water usage" width="552">

*Synthetic dashboard preview: two fictional meters. No real meter data is shown.*

### 8. Calibrate to litres

- [ ] Keep raw pulses until you measure your own scale. Take **two register photos at least a day apart**, and record `meter_count` at the **same radio interval endpoints**. Avoid water use between each endpoint and its photo; a photo and a counter captured at unrelated times are not aligned readings.
- [ ] Use a period with **no missing receiver hours**, enough water use to exceed register rounding, and clear register units. Follow [docs/CALIBRATION.md](docs/CALIBRATION.md) to calculate litres per count and validate it over more days. Do not copy the fictional example factor.
- [ ] Set the verified `litres_per_count` for your ID and restart. Add `last_hour_litres`, `today_litres` and `total_litres` entity mappings to the card's `entities` block, using `sensor.taggle_123456_<key>` with your own ID. In **Settings → Dashboards → Energy**, select the calibrated **total litres** sensor for water. Only future observed usage is added to that total; calibration does not backfill past Energy usage.

### 9. Troubleshooting

| What you see | What to check |
| --- | --- |
| No frames after 65 minutes | SDR USB access, antenna connection/position and host noise. Try a window, higher position, USB extension and gain changes as above. A different channel or unsupported deployment is possible. |
| ID heard but counts unavailable | First configure the ID and leave scan mode. A **24-byte encrypted format** provides identity and diagnostics only: this receiver cannot report that meter's usage over the air or decrypt it. |
| “Device busy” / cannot open SDR | On Docker/Linux, check the DVB kernel driver; also stop other SDR apps or containers holding the dongle. A VM must pass the USB device through to the receiver host. |
| Entities unavailable after 3 hours | No valid frame for three hours makes the meter unavailable. Check receiver logs, antenna, USB and MQTT connection; confirm `scan_minutes: 0`. |
| Usage too high or low | Pulses are not litres until calibrated. Check your scale, register units (m³ × 1000 = litres), aligned timestamps and reception gaps. Daily totals include observed intervals only. |

- [ ] If still stuck, collect the software version and error text. Redact your actual ID and private configuration before sharing anything publicly.

## Reference

The sections below cover configuration, supported formats and operating limits in more detail.

## Hardware and transmitter support

- An RTL-SDR with USB access. The container builds include the **RTL-SDR Blog driver**, including Blog V4 support.
- An antenna suitable for **915–928 MHz**, positioned to receive your meter.
- Home Assistant with its MQTT integration and an MQTT broker.

| Decoded format | Available information |
| --- | --- |
| 18 or 21 bytes, clear format | Meter ID, three raw counter slots, hourly usage, SNR and signal level |
| 24 bytes, encrypted format | Meter ID, SNR, signal level and last seen only |

The default SDR centre frequency is **922.2 MHz**, at **2.4 MS/s**. Reception currently targets the known channel near 922 MHz; this is not a whole-band receiver for every Taggle deployment. Encrypted payloads are not and will not be attacked.

## Find your meter ID

Look for the transmitter label **`ID:xxxxxx`**, usually separate from the mechanical meter's register serial number. All example IDs here are fictional.

If you need to check reception, scan for at least 65 minutes: a transmitter can send only once per hour.

```sh
# With config.json prepared as below; launches rtl_sdr automatically.
taggle-rx --config config.json --scan 65

# Docker, after configuring the image owner (see Publishing):
docker compose run --rm taggle --config /config/options.json --scan 65
```

Scan prints one JSON object per valid frame with the ID, SNR and signal level. It prints counts **only for explicitly configured IDs**, writes no state or logs, and makes no MQTT connection. An empty meter list is allowed while scanning. Verify your own label before configuring an ID; reception does not establish ownership.

## Home Assistant add-on

Add `https://github.com/Spicynostalgia/ha-taggle` under **Settings → Apps (Add-ons) → Store → Repositories**. Install **Taggle water meter**. Home Assistant pulls the versioned amd64 or aarch64 image from GHCR, substituting `{arch}` in the add-on image name.

1. Install an MQTT broker app and configure the Home Assistant MQTT integration.
2. Connect the SDR and set `meter_ids` to your transmitter's decimal ID.
3. Leave `litres_per_count` empty until calibrated. Set `timezone` to match Home Assistant.
4. Start the add-on. A device appears in MQTT for each configured meter.

Example add-on options:

```yaml
meter_ids: [123456]
log_all_meters: false
frequency: 922200000
gain: 40
device: "0"
timezone: UTC
litres_per_count: []
jsonl_logging: false
scan_minutes: 0
```

MQTT credentials come from Supervisor service discovery. To scan, set `scan_minutes: 65`; once finished, set it back to `0` and restart. See [add-on documentation](addon/DOCS.md).

## Standalone Docker

Compose uses `ghcr.io/spicynostalgia/ha-taggle:latest` (amd64/aarch64); use a version such as `:0.1.0` to pin a release. A commented `build` block in [docker-compose.yml](docker-compose.yml) enables local builds.

```sh
cp config.example.json config.json
# Edit config.json: your meter ID, MQTT broker, timezone and SDR options.
# Keep data_dir as /data inside the container.
mkdir -p data
chmod 700 data
chmod 600 config.json
docker compose pull
docker compose up -d
docker compose logs -f
```

The example connects to an **existing** broker. Set `mqtt.host` to a hostname reachable from the container; `localhost` means the container itself. USB mapping is for a Linux host. `device` can be an RTL index or its USB serial. A kernel DVB driver or another SDR application must not hold the device. No transmit software is included.

The receiver restarts the SDR process after disconnects and reanchors incoming samples to wall time. Memory queues are bounded. SDR input backpressure can still cause sample loss, which raw unsigned IQ cannot measure.

## Python and file input

Python **3.11–3.13** on Linux, plus `rtl_sdr`, is supported. NumPy, SciPy, Paho MQTT and timezone data are pinned in [requirements.txt](addon/requirements.txt).

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install .
cp config.example.json config.json
# For a host installation, change data_dir to ./data and mqtt.host to your broker.
taggle-rx --config config.json

# Pipe interleaved unsigned 8-bit I/Q from rtl_sdr:
rtl_sdr -f 922200000 -s 2400000 -g 40 - | taggle-rx --config config.json --input -

# Replay your own cu8 recording; the first sample needs an explicit timestamp:
taggle-rx --config config.json --input own-meter.cu8 --start-utc 2026-01-01T00:00:00Z
```

The package source lives under `addon/taggle_rx` so Home Assistant can build from the add-on directory alone. Root `pyproject.toml` installs that same package.

## Configuration and privacy

[config.example.json](config.example.json) lists the standalone configuration keys. `meter_ids` is required unless `log_all_meters` is explicitly enabled or scan mode is used. Frames from unconfigured IDs are dropped **before state, logs or MQTT** by default. Explicit `log_all_meters: true` permits JSONL logging of other heard IDs; only configured meters get MQTT entities. Keep it disabled for ordinary use.

`jsonl_logging` defaults to false. When enabled, decoded summaries go to daily JSONL files under `data_dir`; raw radio frames and encrypted bodies are never written. Logs have no automatic rotation: manage their retention yourself. Persistent `state.json` contains your meter IDs and usage; keep it private and backed up. Configuration and local data are git-ignored. MQTT payloads contain usage and IDs, so use a trusted broker and network.

## MQTT entities

Each configured meter has one device, with stable entity unique IDs. Default suggested entity IDs are `sensor.taggle_123456_<key>`; Home Assistant may rename them.

| Entity key | Unit | Meaning |
| --- | --- | --- |
| `last_hour` | pulses | Difference between the newest two 16-bit slots |
| `today` | pulses | Observed hourly intervals ending on the local date; partial coverage |
| `meter_count` | pulses | Persisted sum of distinct observed intervals, `total_increasing` |
| `snr` | dB | Median despread correlation SNR estimate |
| `signal_level` | dBFS | Noise-subtracted signal level in the sampled band |
| `last_seen` | timestamp | Time of the last validated radio frame |
| `last_hour_litres` | L | Last hour multiplied by this meter's configured scale |
| `today_litres` | L | Observed daily total multiplied by that scale |
| `total_litres` | L | Persistent calibrated increments, `total_increasing`; select this for Energy |

Litre entities exist only when calibrated and carry `device_class: water`. The count entities require a clear frame; encrypted meters expose diagnostics while usage entities remain unavailable. `meter_count` is an **observed cumulative total**, not the meter register reading. It starts at the sum of the two recoverable intervals, deduplicates overlaps across restarts, handles 16-bit count and 8-bit sequence wraps, and skips unknown gaps. The most recent raw 16-bit slot is included as `raw_count` in attributes.

Calibration changes apply to **future** additions to `total_litres`; they do not revalue past Energy consumption. Daily and hourly litre displays use the current factor. Deleting `state.json` loses the cumulative baseline.

Default topics are `taggle/<id>/state`, `/attributes`, `/available`, `/counts_available` and `taggle/status`, with retained discovery under `homeassistant/sensor/`. A last will marks the receiver offline. Meters become unavailable after three hours without a valid frame. Discovery and cached state are republished on broker reconnect and Home Assistant's MQTT birth message. Use different topic prefixes for separate receiver instances. If you remove a meter or change prefixes, remove its old MQTT device/discovery topics manually.

The receiver recomputes today's observed total once a minute, including at local midnight, without changing `last_seen`. Three slots provide **two** hourly differences; timestamps are approximate transmitter interval endpoints, not utility clock-hour buckets. Missing hours stay missing.

## Dashboard card

Add `https://github.com/Spicynostalgia/ha-taggle` as a **custom Dashboard repository** in HACS, or copy [dist/taggle-card.js](dist/taggle-card.js) to Home Assistant's `www/taggle-card.js`. Add a JavaScript module resource `/local/taggle-card.js?v=0.1.0` for manual installation. HACS installs the committed `dist` file; no frontend build or dependencies are needed. Publishing a GitHub release makes versioned installation available.

Configure entity IDs explicitly (including renamed entities):

```yaml
type: custom:taggle-card
title: Water usage
entities:
  last_hour: sensor.taggle_123456_last_hour
  today: sensor.taggle_123456_today
  meter_count: sensor.taggle_123456_meter_count
  last_seen: sensor.taggle_123456_last_seen
  snr: sensor.taggle_123456_snr
  signal_level: sensor.taggle_123456_signal_level
```

Add `last_hour_litres`, `today_litres` and `total_litres` to use litres automatically. An `entities` list also works for default suggested entity names. Alternatively use the Home Assistant **device registry ID**, not the transmitter number:

```yaml
type: custom:taggle-card
device: your-home-assistant-device-registry-id
```

For several meters, set `meters` to a list of objects, each containing `name` and `entities` or `device`. The card follows your Home Assistant theme, language and timezone, shows missing/unavailable readings explicitly, and provides a 48-hour chart with an accessible values table. It reads only authenticated Home Assistant states and its entity registry.

## Calibration

No litres-per-count value is assumed. Use two or more **aligned** physical register readings or an export from your utility, together with the radio's cumulative observed `meter_count`. Do not fit across reception gaps. See [the calibration guide](docs/CALIBRATION.md).

```sh
taggle-calibrate readings.csv --register-unit m3
```

The helper prints a proposed scale and residual; it never modifies configuration. A combined CSV has `time,register_reading,meter_count` columns. Alternatively pass a register CSV (`time,register_reading`) and `--counts counts.csv` (`time,meter_count`) with exact matching timestamps.

## Protocol and limitations

The radio uses BPSK with a 4095-chip m-sequence per coded bit, approximately 4.8 Mchip/s. Its forward polynomial is **x^12+x^9+x^6+x^5+x^2+x+1** (`0x1267`). A 104-symbol constant preamble precedes a rate-1/2, K=7 convolutional code (`0x6d`, `0x4f`). Decoded frames start with `c0`, have a nibble-aligned 20-bit ID and header CRC, and end in CRC-8 (`0x07`) plus a zero tail byte. Clear frames contain a three-slot counter history. [Protocol details](docs/PROTOCOL.md) describe exact offsets, recurrence and CRC boundaries.

This implementation receives only part of the wideband spread signal. Antenna quality, noise, collisions, USB loss, radio clock drift and host CPU performance affect reception. Daily totals can be incomplete, counter resets are ambiguous, flag meanings remain unknown, and modulo counter differences cannot distinguish multiple wraps. It does not provide billing-grade accuracy. Test coverage validates synthetic signals, not compatibility with every transmitter.

## Development

Regenerate the README screenshots with Python's standard library and an installed Chromium:

```sh
CHROME=/absolute/path/to/chromium python3 scripts/screenshots.py
```

The script serves the repository over loopback HTTP and writes four 2× PNGs into `docs/images/`. The [screenshot harness](docs/screenshots/harness.html) accepts `theme=light|dark`, `width=NNN` (card width in CSS pixels) and `scenario=calibrated|raw|multi`. It fixes the clock and uses only fictional IDs and synthetic 48-hour history, with missing and zero-use hours. Preview it through an HTTP server, not `file://`. Use the same Chromium version and fonts for repeatable pixels, and commit the generated PNGs after inspecting them.

```sh
pip install -e '.[dev]'
ruff check .
pytest -q
node --test tests/card.test.cjs
python scripts/check_release.py
```

Tests generate fake frames and filtered PN-modulated IQ from the project's own encoder; no captures, real frames or private analysis artifacts are included. CI tests Python 3.11/3.13 and builds both container variants for amd64/aarch64 without pushing images. See [CONTRIBUTING.md](CONTRIBUTING.md), [CHANGELOG.md](CHANGELOG.md) and [RELEASE-CHECK.md](RELEASE-CHECK.md).

## Publishing

**Forking?** Before your first release, run `python scripts/set_owner.py your-github-name` with the GitHub user or organization hosting your fork (this repository is already set to `spicynostalgia`). It replaces the literal `GITHUB_OWNER` placeholder everywhere in the distributable files with the lowercase owner; commit the result once. In particular, `addon/config.yaml` must contain `image: ghcr.io/GITHUB_OWNER/ha-taggle-addon-{arch}` with your owner substituted. Keep `{arch}` literal: Home Assistant substitutes `amd64` or `aarch64`, and uses the add-on version as the image tag. The script also configures Compose and updates documentation.

Keep `addon/config.yaml`, root `pyproject.toml` and `addon/pyproject.toml` versions equal, and add the matching `## <version>` section to `CHANGELOG.md` (also update `addon/CHANGELOG.md`). A pushed tag such as `v0.1.0` triggers [release.yml](.github/workflows/release.yml); it rejects version mismatches or missing release notes before publishing. You can validate locally with:

```sh
python scripts/prepare_release.py v0.1.0 --notes /tmp/taggle-release-notes.md
```

The workflow uses only the built-in `GITHUB_TOKEN`, with `packages: write` and `contents: write`. It publishes `ghcr.io/<owner>/ha-taggle-addon-amd64:<version>` and `ha-taggle-addon-aarch64:<version>`, plus the standalone `ghcr.io/<owner>/ha-taggle:<version>` and `:latest` manifest for `linux/amd64` and `linux/arm64` using Buildx/QEMU. Tags omit the leading `v`. After all images succeed, it creates a GitHub Release using that version's changelog section.

After the first publication, make all three GHCR packages public in their package settings so Home Assistant and Compose can pull without credentials. Ensure organization policy permits Actions package publishing. Pull-request CI remains build-only and never logs in or pushes images. See [RELEASE-CHECK.md](RELEASE-CHECK.md) for validation limits.

## License and disclaimer

The application and card are MIT licensed; see [LICENSE](LICENSE). Container dependencies, including the separately executed GPL-licensed RTL-SDR Blog driver, retain their own licenses. The driver's source revision and license are preserved by the Docker builds. [Release provenance](RELEASE-CHECK.md) explains the application license decision.

Unofficial; not affiliated with Taggle Systems or any utility. Receive-only, for reading your own meter. Respect local radio and privacy laws. Encrypted payloads are not and will not be attacked.
