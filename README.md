# ha-taggle: hourly water use in Home Assistant

[![Latest release](https://img.shields.io/github/v/release/Spicynostalgia/ha-taggle)](https://github.com/Spicynostalgia/ha-taggle/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/Spicynostalgia/ha-taggle/ci.yml?branch=main&label=CI)](https://github.com/Spicynostalgia/ha-taggle/actions/workflows/ci.yml)
[![MIT licence](https://img.shields.io/github/license/Spicynostalgia/ha-taggle)](LICENSE)
[![Home Assistant add-on](https://img.shields.io/badge/Home%20Assistant-add--on-41BDF5)](#a-home-assistant-os-add-on)
[![HACS custom repository](https://img.shields.io/badge/HACS-custom-41BDF5)](#dashboard-card)
[![Councils reported](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Spicynostalgia/ha-taggle/main/docs/compat-badge.json)](https://github.com/Spicynostalgia/ha-taggle/wiki/Is-My-Area-Covered)
[![Website](https://img.shields.io/badge/website-ha--taggle.dancloud.au-2bb3d6)](https://ha-taggle.dancloud.au)

Receive your Taggle water meter locally with an RTL-SDR, then send hourly usage to Home Assistant over MQTT.
The supported 922 MHz radio format is **DSSS/BPSK, not LoRa or LoRaWAN**. The receiver never transmits.

**Only one Gladstone, QLD transmitter has been field-verified**, with an RTL-SDR Blog V4 on an owner-confirmed Elster (Honeywell) V100.
Other models and regions are unverified. Generated tests do not establish compatibility with another transmitter.

<img src="docs/images/card-light.png" width="552" alt="Taggle dashboard card with fictional calibrated usage, hourly history and seven-day totals.">

*Fictional calibrated data. Your first readings are pulses. [More screenshots and the field test](https://github.com/Spicynostalgia/ha-taggle/wiki/Tested-Hardware).*

## Quick start

These steps use receiver and card **0.3.1**. The field radio test used **0.2.1**.
You need HA with MQTT, a Linux amd64/aarch64 host or HA OS, USB access, and an antenna suitable for 915–928 MHz.
A VM needs USB passthrough. [Hardware and antenna setup](https://github.com/Spicynostalgia/ha-taggle/wiki/Hardware-and-Antennas).

The **transmitter ID** on the radio label goes in `meter_ids`; it is different from the mechanical meter's serial number.
All IDs below are fictional. [Find yours safely](https://github.com/Spicynostalgia/ha-taggle/wiki/Finding-Your-Meter).

Clear frames carry pulse counters, **not the dial reading**. Litres per pulse and the starting offset need calibration.
Supported encrypted frames provide **ID and signal diagnostics only**, with no usage.

### A. Home Assistant OS add-on

1. Plug in the RTL-SDR with its antenna connected. Stop other apps using that receiver.
   USB or startup trouble? [Add-on guide](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-the-Add-on).
2. Install/start **Mosquitto broker** from **Settings → Apps (Add-ons) → Store** and configure HA's **MQTT** integration.
   [Add this repository](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FSpicynostalgia%2Fha-taggle), then install **Taggle water meter**.
   Supervisor supplies MQTT credentials. [Full installation guide](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-the-Add-on).
3. In the add-on's **Configuration**, keep the other options and set these for a first scan:

   ```yaml
   meter_ids: []
   scan_minutes: 65
   timezone: Australia/Brisbane
   litres_per_count: []
   ```

   Use **your HA timezone**. Neighbourhood comparison is on by default; set `neighbourhood: false` before starting to disable it.
   [Comparison assumptions and privacy](https://github.com/Spicynostalgia/ha-taggle/wiki/Neighbourhood-Comparison).
   **Save → Start**, then watch **Logs**. Scans print IDs privately and do not publish MQTT devices.
   Allow **65 minutes** once startup is healthy. [Scan output and reception help](https://github.com/Spicynostalgia/ha-taggle/wiki/First-Scan-and-Tap-Test).
4. Confirm your own transmitter using its label or the [water-use check](https://github.com/Spicynostalgia/ha-taggle/wiki/First-Scan-and-Tap-Test#part-2-the-water-use-check).
   Set `meter_ids: [123456]` using your ID, restore `scan_minutes: 0`, then **Save → Start/Restart** and enable **Start on boot**.
5. Open **Settings → Devices & services → MQTT → Devices → Taggle [your ID]**.
   Discovery appears before the first radio reading; allow another hourly transmission for usage.
   [No device or no readings?](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting) Then [calibrate litres per pulse](#calibrate-litres-per-pulse).

### B. Docker

1. Plug in the RTL-SDR and antenna on the receiver's Linux host. Stop other programs using it.
   Use an existing MQTT broker and HA MQTT integration. [Docker, USB and broker setup](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-with-Docker).
2. Get the receiver files on that host:

   ```sh
   git clone https://github.com/Spicynostalgia/ha-taggle.git
   cd ha-taggle
   git checkout --detach v0.3.1
   cp config.example.json config.json
   mkdir -p data
   chmod 700 data
   chmod 600 config.json
   ```

   Edit `config.json`: start with `"meter_ids": []`, set `timezone` to match HA, and leave `"litres_per_count": {}`.
   Set `host`, `username` and `password` inside the existing `mqtt` object. Use the broker's LAN address;
   `localhost` means the receiver container. Keep `"data_dir": "/data"`.
   Comparison is on by default; use `"neighbourhood": false` to disable collection.
   [Configuration and JSON help](https://github.com/Spicynostalgia/ha-taggle/wiki/Installing-with-Docker#step-2-edit-configjson).
3. Pull the image and scan for your transmitter:

   ```sh
   docker compose pull taggle
   docker compose stop taggle
   docker compose run --rm taggle --config /config/options.json --scan 65
   ```

   Stop normal reception before every scan. Scans print IDs privately, with no MQTT or saved state.
   Confirm your ID using the label or [water-use check](https://github.com/Spicynostalgia/ha-taggle/wiki/First-Scan-and-Tap-Test#part-2-the-water-use-check).
   [Nothing heard?](https://github.com/Spicynostalgia/ha-taggle/wiki/First-Scan-and-Tap-Test#nothing-heard)
4. When the scan ends, set `"meter_ids": [123456]` to **your** ID in `config.json`, then start normal reception:

   ```sh
   docker compose up -d taggle
   docker compose logs -f taggle
   ```

   Check `Reading samples in async mode...` and `MQTT connected`.
   Ctrl+C leaves the log viewer; the receiver keeps running. [Startup help](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting).
5. Open **Settings → Devices & services → MQTT → Devices → Taggle [your ID]**.
   Devices appear when MQTT connects; usage waits for a transmission, usually hourly.
   [No sensors?](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting#home-assistant-shows-nothing) Then calibrate below.

### Calibrate litres per pulse

Use the card's **Read your dial** panel, or the MQTT device's **Dial unit** selector and **Dial reading** text box.
Guided calibration needs no configuration edit or restart.

1. Just after a transmission, read the full dial within **10 minutes**, before water use. Choose **m³, kL or L** and save.
2. Use about **20–50 L** during the hour; reuse it. This is guidance, not a minimum-usage gate.
3. Read and save again just after the **next transmission**, normally an hour later. Follow **Calibration status** if it asks for another reading.

The tested V100 matches **5 L/pulse**; a V100 4×4 counter is specified at **0.5 L/pulse**. Still calibrate yours.
The radio counter has an arbitrary offset, so multiplying it by a pulse size does not reconstruct the dial.
Check the estimated **Meter reading** against your physical dial; this is experimental, not billing-grade measurement.
[Calibration, photo times and corrections](https://github.com/Spicynostalgia/ha-taggle/wiki/Calibration) · [Meter types and pulse sizes](https://github.com/Spicynostalgia/ha-taggle/wiki/Meter-Types-and-Pulse-Sizes).

## Will it work for me?

Confirm Taggle **at your property** before buying hardware. A council portal or similar-looking transmitter proves little.
NB-IoT is unsupported. The default SDR centre is **922.2 MHz**; it does not scan every Taggle channel.
[Coverage and encryption limits](https://github.com/Spicynostalgia/ha-taggle/wiki/Is-My-Area-Covered) · [Confirmed reports](docs/COMPATIBILITY.md).

## Dashboard card

The card is optional; standard HA sensor cards work too.
Install **ha-taggle 0.3.1** through **HACS → Custom repositories → Dashboard** using this repository URL.
HACS installs the card; the receiver is separate. [HACS and manual installation](https://github.com/Spicynostalgia/ha-taggle/wiki/Dashboard-Card).

In **Edit dashboard → Add card → Manual**, use the HA device registry ID from the end of your Taggle device page's URL:

```yaml
type: custom:taggle-card
device: your-home-assistant-device-id
```

This is the long HA device ID, not transmitter number `123456`.
[Entity mappings, multiple meters and history](https://github.com/Spicynostalgia/ha-taggle/wiki/Dashboard-Card) · [Possible-leak hint](https://github.com/Spicynostalgia/ha-taggle/wiki/Leak-Detection).

## Energy dashboard

After calibration, select **Meter reading** under **Settings → Dashboards → Energy → Water**: [choose one source per supply](https://github.com/Spicynostalgia/ha-taggle/wiki/Energy-Dashboard).

## Troubleshooting

- **Startup fails / device busy:** stop competing SDR programs and check USB access, passthrough, power and cables. [USB help](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting#the-dongle-wont-open).
- **Nothing heard after a healthy 65-minute listen:** check antenna placement and computer noise; try a USB extension. [Reception help](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting#nothing-received).
- **No MQTT devices:** check configured IDs, normal mode, `MQTT connected`, and HA's broker/discovery settings. [Discovery help](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting#home-assistant-shows-nothing).

[All troubleshooting](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting) · [FAQ](https://github.com/Spicynostalgia/ha-taggle/wiki/FAQ) · [Back up and update](https://github.com/Spicynostalgia/ha-taggle/wiki/Configuration-Reference#back-up-and-update).

## How we decoded it

[Decoding Taggle at 922 MHz](docs/blog/decoding-taggle-922mhz.md) · [Protocol specification](docs/PROTOCOL.md) · [Research and prior art](https://github.com/Spicynostalgia/ha-taggle/wiki/Research-and-Prior-Art).

## Fork it for your own meter

The application and card are **MIT licensed**. Start with [config.example.json](config.example.json) or the add-on options:

- Set `meter_ids` to your own decimal transmitter IDs.
- Set the SDR centre with `frequency`. The default is **922200000 Hz**; changing it does not add support for another radio protocol.
- Calibrate pulse size with dial readings. `litres_per_count` is an optional manual pin, not a universal default.
- Set your MQTT broker and topic/discovery prefixes for the target HA installation. The add-on gets broker credentials from Supervisor.

[Settings and supported ranges](https://github.com/Spicynostalgia/ha-taggle/wiki/Configuration-Reference) · [Contributing](CONTRIBUTING.md).

Only receive your own meter's data for individual usage. The decoder **never decrypts encrypted frames**.
Keep scans, IDs, photos, private logs and configuration out of public posts.
[Neighbourhood comparison and its off switch](https://github.com/Spicynostalgia/ha-taggle/wiki/Neighbourhood-Comparison) · [Privacy and legal](https://github.com/Spicynostalgia/ha-taggle/wiki/Privacy-and-Legal).

## Help and reporting

[Report your result](https://github.com/Spicynostalgia/ha-taggle/issues/new/choose), working or stuck.
Include version, install method, council/utility, receiver model, and whether you got usage, ID only, or nothing.
Frame length and signal details are optional; **unknown is fine**. Do not enable broad logging just to find them.
Replace IDs with fictional `123456`, cover barcodes, and omit credentials, private configuration and radio captures.
[Full sharing checklist](https://github.com/Spicynostalgia/ha-taggle/wiki/Reporting-Compatibility).

## AI disclosure

Most reverse engineering, code, tests, diagrams and docs were produced by **Claude Code (Opus)** and **OpenAI Codex**.
A human chose the goals, captured their own meter's signal, checked it against the dial and approved every change.
Read the code before trusting it. [Authorship, costs and water/energy estimates](https://github.com/Spicynostalgia/ha-taggle/wiki/AI-Disclosure).

## Licence and disclaimer

The application and card use the [MIT licence](LICENSE). Container dependencies retain their own licences, including the separately executed GPL RTL-SDR Blog driver.
Unofficial; not affiliated with Taggle Systems or any utility. Receive-only, for your own meter. Respect local radio and privacy laws.
Encrypted payloads are not and will not be attacked. [Licence details and release provenance](https://github.com/Spicynostalgia/ha-taggle/wiki/Privacy-and-Legal#licence).
