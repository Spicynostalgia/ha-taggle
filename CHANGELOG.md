# Changelog

## Unreleased

- Add a possible-leak hint for configured meters from continuous hourly usage or local night flow, with configurable rules, MQTT binary sensor attributes and a dashboard badge.
- Limit MQTT sensor display precision and round published measurements without changing stored usage or calibration.
- Log MQTT connections, receiver startup, configured-meter frames and a 15-minute listening heartbeat with counts only for other meters.
- Add UTC frame timestamps and one-decimal signal measurements to scan JSON output.
- Show a neutral first-reading message on fresh dashboard cards while preserving warnings for previously seen meters.
- Docs: restructure the README for beginners, add real hardware screenshots and tested Docker/broker setup, and link technical detail in the wiki.

## 0.2.1

- Fix MQTT discovery defaults for Home Assistant 2026.4+ and align sensor names with documented entity IDs.
- Fix card device lookup confusing today with the neighbourhood comparison, including existing name-derived and renamed entities.
- Refresh retained daily and neighbourhood state after file input finishes.
- Create JSONL logs with mode 0600 and new data directories with mode 0700.
- Clarify Python 3.11–3.13 support, Debian/Ubuntu venv setup, replay wall-clock behavior and add-on options.

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
