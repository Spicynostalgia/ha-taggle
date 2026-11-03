# Changelog

## 0.3.1

- Allow one pulse of quantisation before choosing a nonstandard calibration fit; the overnight replay's 585 L over 116 counts now resolves to 5 L/pulse.
- Keep the neighbourhood comparison available when a dial reading is entered or the ten-minute read window closes.
- Prefix receiver logs with local timestamps and UTC offsets.
- Explain the neighbourhood’s expected early-morning wait, midnight interval accounting and drifting transmission estimates; clarify the last-ten-readings attribute limit.

## 0.3.0

Released 2026-11-03.

- Replace the number and separate photo-time controls with one validated Dial reading text box: optional time travels with its reading; accept HHMM, at/@ and comma decimals, preserve JSON, and remove old discovery/pending time on upgrade.
- Guide calibration over one hour: read within ten minutes after a transmission, use 20–50 L (reuse it), then read just after the next transmission. Add Good time to read the dial, countdown and three-step card guidance, exact flags and a phone reminder example.
- Remove the minimum-usage gate and retired option; name ambiguous standard sizes, tolerate obsolete saved options with a warning, and include typed dial resolution in bounds, fits and residual checks.
- Move reset to Configuration as Delete all dial readings with a delete-sweep icon and an explanation in calibration attributes; clarify that m³ = kL.

- Add guided calibration from manual dial readings: m³/kL/L selector, reading box, optional photo time and reset, with automatic standard pulse selection and an absolute meter reading for Energy.
- Align readings to persisted counter intervals, resolve unambiguous missing-slot wraps, validate units/typos and pinned factors, and report bounds, weighted residuals and exclusions.
- Show the next expected local transmission time and dial-reading guidance in Home Assistant and the card; publish litre entities automatically after calibration.
- Persist calibration in versioned private state, migrate old checkpoints, and restore MQTT command subscriptions after reconnect and Home Assistant birth.
- Make manual guided calibration the beginner path; document maths/CLI and advanced utility automation separately.

- Limit MQTT sensor display precision and round published measurements without changing stored usage or calibration.
- Log MQTT connections, receiver startup, configured-meter frames and a 15-minute listening heartbeat with counts only for other meters.
- Add UTC frame timestamps and one-decimal signal measurements to scan JSON output.
- Show a neutral first-reading message on fresh dashboard cards while preserving warnings for previously seen meters.
- Docs: restructure the README for beginners, add real hardware screenshots and tested Docker/broker setup, and link technical detail in the wiki.
- Add configurable possible-leak hints from hourly usage for configured meters, with a `problem` binary sensor, coverage attributes and persistent recovery rules.

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
