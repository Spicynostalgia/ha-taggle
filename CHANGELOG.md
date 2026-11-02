# Changelog

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
