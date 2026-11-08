# ha-taggle: hourly water use in Home Assistant

[![Latest release](https://img.shields.io/github/v/release/Spicynostalgia/ha-taggle)](https://github.com/Spicynostalgia/ha-taggle/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/Spicynostalgia/ha-taggle/ci.yml?branch=main&label=CI)](https://github.com/Spicynostalgia/ha-taggle/actions/workflows/ci.yml)
[![MIT licence](https://img.shields.io/github/license/Spicynostalgia/ha-taggle)](LICENSE)
[![Home Assistant add-on](https://img.shields.io/badge/Home%20Assistant-add--on-41BDF5)](#a-home-assistant-os-add-on)
[![HACS custom repository](https://img.shields.io/badge/HACS-custom-41BDF5)](#dashboard-card)
[![Councils reported](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Spicynostalgia/ha-taggle/main/docs/compat-badge.json)](https://github.com/Spicynostalgia/ha-taggle/wiki/Is-My-Area-Covered)
[![Website](https://img.shields.io/badge/website-ha--taggle.dancloud.au-2bb3d6)](https://ha-taggle.dancloud.au)

Receive your Taggle water meter locally with an RTL-SDR and send hourly water use to Home Assistant over MQTT.

[How I decoded it](docs/blog/decoding-taggle-922mhz.md).

<img src="docs/images/card-light.png" width="552" alt="Taggle dashboard card with fictional calibrated usage, hourly history and seven-day totals.">

*Fictional calibrated data. Your first readings are pulses. [More screenshots and the field test](https://github.com/Spicynostalgia/ha-taggle/wiki/Tested-Hardware).*

## Will it work for me?

Confirm that **your property** uses Taggle before buying hardware. A council portal or similar-looking transmitter is not confirmation.

| Check | What to expect |
| --- | --- |
| Radio | **922 MHz DSSS/BPSK**; no LoRa, LoRaWAN or NB-IoT. Never transmits. |
| Frequency | Defaults to a **922.2 MHz** SDR centre frequency; does not scan every Taggle channel. |
| Clear frames | **Pulse counters**, not dial readings. Calibrate litres per pulse and the starting offset. |
| Supported encrypted frames | **ID and signal diagnostics only**, with no usage. The decoder never decrypts or attacks encrypted payloads. |
| Field testing | One owner-confirmed **Elster (Honeywell) V100** in **Gladstone, QLD**, using an **RTL-SDR Blog V4**. Others may work but are unverified; generated tests check code, not transmitter compatibility. |

[Coverage and encryption limits](https://github.com/Spicynostalgia/ha-taggle/wiki/Is-My-Area-Covered) · [Confirmed reports](docs/COMPATIBILITY.md).

## Quick start

Use receiver and card **0.3.1**; the field radio test used **0.2.1**.
Before either installation:

- You need **HA with MQTT**, **HA OS or Linux amd64/aarch64**, USB access and a **915–928 MHz antenna**. VMs need USB passthrough. [Hardware and antenna setup](https://github.com/Spicynostalgia/ha-taggle/wiki/Hardware-and-Antennas).
- Connect the antenna, plug in the RTL-SDR and stop other programs using it.
- Use the radio label's **transmitter ID** for `meter_ids`, not the mechanical meter's serial number. Example IDs are fictional. [Find yours safely](https://github.com/Spicynostalgia/ha-taggle/wiki/Finding-Your-Meter).
- **Neighbourhood comparison defaults to on.** Opt out before starting with the setting shown below. [Comparison assumptions and privacy](https://github.com/Spicynostalgia/ha-taggle/wiki/Neighbourhood-Comparison).

Choose **[HA OS add-on](#a-home-assistant-os-add-on)** or **[Docker](#b-docker)**.

### A. Home Assistant OS add-on

[Add-on guide](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-the-Add-on) for USB and startup help.

1. **Set up MQTT.** Install and start **Mosquitto broker** in **Settings → Apps (Add-ons) → Store**. Configure HA's **MQTT** integration.
2. **Install the receiver.** [Add this repository](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FSpicynostalgia%2Fha-taggle), then install **Taggle water meter**. Supervisor supplies MQTT credentials. [Full installation guide](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-the-Add-on).
3. **Scan for your transmitter.** Open the add-on's **Configuration**. Keep the other options and set:

   ```yaml
   meter_ids: []
   scan_minutes: 65
   timezone: Australia/Brisbane
   litres_per_count: []
   ```

   Use **your HA timezone**; `neighbourhood: false` turns off collection.
   Select **Save → Start**, open **Logs** and listen for **65 minutes** after startup succeeds.
   Scans print IDs privately without publishing MQTT devices. [Scan output and reception help](https://github.com/Spicynostalgia/ha-taggle/wiki/First-Scan-and-Tap-Test).
4. **Start normal reception.** Confirm your transmitter ID from its label or the [water-use check](https://github.com/Spicynostalgia/ha-taggle/wiki/First-Scan-and-Tap-Test#part-2-the-water-use-check).
   Set `meter_ids: [123456]` with your ID and restore `scan_minutes: 0`. Select **Save → Start/Restart**. Enable **Start on boot**.
5. **[Find your device](#find-your-device).** [No device or no readings?](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting)

### B. Docker

Use your existing MQTT broker and HA MQTT integration. [Docker, USB and broker setup](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-with-Docker).

1. **Get the receiver files** on the Linux host with the RTL-SDR:

   ```sh
   git clone https://github.com/Spicynostalgia/ha-taggle.git
   cd ha-taggle
   git checkout --detach v0.3.1
   cp config.example.json config.json
   mkdir -p data
   chmod 700 data
   chmod 600 config.json
   ```

2. **Configure the receiver.** Edit `config.json`: start with `"meter_ids": []`, set `timezone` to match HA, and leave `"litres_per_count": {}`.
   Set `host`, `username` and `password` in the existing `mqtt` object. Use the broker's LAN address: `localhost` means the receiver container. Keep `"data_dir": "/data"`; `"neighbourhood": false` turns off collection.
   [Configuration and JSON help](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-with-Docker#step-2-edit-configjson).
3. **Scan for your transmitter.** Pull the image and run:

   ```sh
   docker compose pull taggle
   docker compose stop taggle
   docker compose run --rm taggle --config /config/options.json --scan 65
   ```

   Stop normal reception before every scan. Scans print IDs privately. They do not use MQTT or save state.
   Confirm your ID using the label or [water-use check](https://github.com/Spicynostalgia/ha-taggle/wiki/First-Scan-and-Tap-Test#part-2-the-water-use-check).
   [Nothing heard?](https://github.com/Spicynostalgia/ha-taggle/wiki/First-Scan-and-Tap-Test#nothing-heard)
4. **Start normal reception.** After the scan, set `"meter_ids": [123456]` with your ID in `config.json`, then run:

   ```sh
   docker compose up -d taggle
   docker compose logs -f taggle
   ```

   Check `Reading samples in async mode...` and `MQTT connected`.
   Press Ctrl+C to leave the log viewer. The receiver keeps running. [Startup help](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting).
5. **[Find your device](#find-your-device).** [No sensors?](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting#home-assistant-shows-nothing)

### Find your device

Open **Settings → Devices & services → MQTT → Devices → Taggle [your ID]**.
Discovery appears when MQTT connects, before radio readings. Usage follows the next transmission, usually hourly. Then [calibrate litres per pulse](#calibrate-litres-per-pulse).

### Calibrate litres per pulse

Use the card's **Read your dial** panel or the MQTT device's **Dial unit** selector and **Dial reading** text box. No configuration edit or restart needed.

1. Read the full dial within **10 minutes** after a transmission, before using water. Choose **m³, kL or L** and save.
2. Use about **20–50 L** during the hour and reuse the water. This is guidance, not a minimum.
3. Read and save just after the **next transmission**, normally an hour later. If **Calibration status** asks for another reading, take one.

The tested V100 matches **5 L/pulse**. The V100 4×4 counter specification gives **0.5 L/pulse**. Calibrate your own meter.
The radio counter's arbitrary offset means pulse size alone cannot reconstruct the dial reading.
Check the estimated **Meter reading** against your dial. The estimate is experimental and unsuitable for billing.
[Calibration, photo times and corrections](https://github.com/Spicynostalgia/ha-taggle/wiki/Calibration) · [Meter types and pulse sizes](https://github.com/Spicynostalgia/ha-taggle/wiki/Meter-Types-and-Pulse-Sizes).

## Dashboard card

The card is optional; standard HA sensor cards also work. Install **ha-taggle 0.3.1** through **HACS → Custom repositories → Dashboard** using this repository URL. HACS installs the card; install the receiver separately. [HACS and manual installation](https://github.com/Spicynostalgia/ha-taggle/wiki/Dashboard-Card).

Copy the HA device registry ID from the end of your Taggle device page's URL. Under **Edit dashboard → Add card → Manual**, enter:

```yaml
type: custom:taggle-card
device: your-home-assistant-device-id
```

Use the long HA device ID here, not the transmitter number `123456`.
[Entity mappings, multiple meters and history](https://github.com/Spicynostalgia/ha-taggle/wiki/Dashboard-Card) · [Possible-leak hint](https://github.com/Spicynostalgia/ha-taggle/wiki/Leak-Detection).

## Energy dashboard

After calibration, open **Settings → Dashboards → Energy → Water**. Select **Meter reading**: [choose one source per supply](https://github.com/Spicynostalgia/ha-taggle/wiki/Energy-Dashboard).

## Troubleshooting

- **Startup fails / device busy:** stop other SDR programs. Check USB access, passthrough, power and cables. [USB help](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting#the-dongle-wont-open).
- **Nothing heard after 65 minutes with the receiver running:** check antenna placement and computer noise. Try a USB extension. [Reception help](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting#nothing-received).
- **No MQTT devices:** check the configured IDs and run normal mode. Look for `MQTT connected` and check HA's broker/discovery settings. [Discovery help](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting#home-assistant-shows-nothing).

[All troubleshooting](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting) · [FAQ](https://github.com/Spicynostalgia/ha-taggle/wiki/FAQ) · [Back up and update](https://github.com/Spicynostalgia/ha-taggle/wiki/Configuration-Reference#back-up-and-update).

## How I decoded it

[Decoding Taggle at 922 MHz](docs/blog/decoding-taggle-922mhz.md) · [Protocol specification](docs/PROTOCOL.md) · [Research and prior art](https://github.com/Spicynostalgia/ha-taggle/wiki/Research-and-Prior-Art).

## Fork it for your own meter

The application and card are **MIT licensed**. Start with [config.example.json](config.example.json) or the add-on options:

- Set `meter_ids` to your own decimal transmitter IDs.
- Set the SDR centre with `frequency` (default **922200000 Hz**). Changing it does not add support for another radio protocol.
- Calibrate pulse size with dial readings. Use `litres_per_count` to pin a value manually if needed. There is no universal default.
- Set your MQTT broker and topic/discovery prefixes for the target HA installation. The add-on gets broker credentials from Supervisor.

[Settings and supported ranges](https://github.com/Spicynostalgia/ha-taggle/wiki/Configuration-Reference) · [Contributing](CONTRIBUTING.md).

Use only your own meter's data for individual usage. Keep scans, IDs, photos, private logs and configuration out of public posts.
[Neighbourhood comparison and its off switch](https://github.com/Spicynostalgia/ha-taggle/wiki/Neighbourhood-Comparison) · [Privacy and legal](https://github.com/Spicynostalgia/ha-taggle/wiki/Privacy-and-Legal).

## Help and reporting

[Report your result](https://github.com/Spicynostalgia/ha-taggle/issues/new/choose), working or stuck.
Include version, install method, council/utility, receiver model and result: usage, ID only, or nothing.
Add frame length and signal details if known. **Unknown is fine**; do not enable broad logging to find them.
Replace IDs with fictional `123456` and cover barcodes. Leave out credentials, private configuration and radio captures.
[Full sharing checklist](https://github.com/Spicynostalgia/ha-taggle/wiki/Reporting-Compatibility).

## AI disclosure

**Claude Code (Opus)** and **OpenAI Codex** produced most of the reverse engineering, code, tests, diagrams and docs.
A human chose the goals, captured their own meter's signal, checked it against the dial and approved every change.
Read the code before trusting it. [Authorship, costs and water/energy estimates](https://github.com/Spicynostalgia/ha-taggle/wiki/AI-Disclosure).

## Licence and disclaimer

The application and card use the [MIT licence](LICENSE). Container dependencies keep their own licences. This includes the GPL RTL-SDR Blog driver, which runs separately.
This project is unofficial and has no affiliation with Taggle Systems or any utility. Respect local radio and privacy laws. [Licence details and release provenance](https://github.com/Spicynostalgia/ha-taggle/wiki/Privacy-and-Legal#licence).
