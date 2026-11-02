# Changelog

## 0.3.0

Released 2026-11-03.

- Enter manual dial readings in Home Assistant to calibrate litres per pulse and the starting offset in 0.3.0. The guided route needs no maths or receiver restart and provides an estimated Meter reading for Energy.
- Choose m³/kL/L, enter an older photo with its original time, and correct or reset stored readings; follow Calibration status when more normal use or another transmission is needed.
- Align readings to persisted counter intervals, resolve unambiguous missing-slot wraps, validate units/typos and pinned factors, and report bounds, weighted residuals and exclusions.
- Show the next expected local transmission time and dial-reading guidance in Home Assistant and the card; publish litre entities automatically after calibration.
- Persist calibration in versioned private state, migrate old checkpoints, and restore MQTT command subscriptions after reconnect and Home Assistant birth.
- Make manual guided calibration the beginner path; document maths/CLI and advanced utility automation separately.
- Add a possible-leak hint for configured meters from continuous hourly usage or local night flow, with configurable rules, MQTT binary sensor attributes and a dashboard badge.
- Show tidier numbers in Home Assistant without changing stored usage or calibration.
- Add startup and MQTT connection messages, configured-meter updates and a listening summary every 15 minutes to help check reception; other meters appear as counts only.
- Add the radio message's UTC time and one-decimal signal measurements to scan output.
- Show a friendly waiting message on new dashboard cards; preserve warnings when a previously seen meter loses reception.
- Docs: clarify dial units, photo times, calibration corrections, Energy totals and backup steps; complete authenticated broker and no-HACS card setup, separate scans from normal reception, and document the MQTT neighbourhood percentage limitation. Preserve the 0.2.1 hardware-test record separately from 0.3.0 features.

## 0.2.1

- Fix MQTT discovery defaults for Home Assistant 2026.4+ and align sensor names with documented entity IDs.
- Fix card device lookup confusing today with the neighbourhood comparison, including existing name-derived and renamed entities.
- Refresh retained daily and neighbourhood state after file input finishes.
- Create JSONL logs with mode 0600 and new data directories with mode 0700.
- Clarify Python 3.11–3.13 support, Debian/Ubuntu venv setup, replay wall-clock behaviour and add-on options.

## 0.2.0

- Add anonymous neighbourhood comparison enabled by default, with salted HMAC identities, a minimum three-meter privacy floor, coverage qualification and seven-day pruning.
- Publish aggregate average/median usage and per-meter comparisons; encrypted neighbours contribute only to the heard count.
- Add a compact comparison row to the dashboard card and document calibration assumptions, partial days and privacy controls.

## 0.1.0

- Package the bounded RTL-SDR receiver with clear-format decoding, FEC and CRC validation.
- Add private-by-default filtering and a scan mode for finding your own transmitter.
- Publish persistent observed usage and diagnostics with Home Assistant MQTT discovery.
- Support per-meter calibration and cumulative water entities for Energy.
- Provide an amd64/aarch64 Home Assistant add-on and a standalone Docker build with Blog V4 support.
- Add a dependency-free, configurable Lovelace card and HACS distribution metadata.
- Provide a generic CSV calibration helper, synthetic IQ tests, release checks and build-only CI.
- Automate version-checked GHCR releases for both architectures and GitHub Release notes; document one-time image owner setup.
