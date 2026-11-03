# Independent verification of 0.3.1

Reviewed the four commits in `0abe2e1..2a5a51e` with `git log -p`, then verified the local corrections below on 2026-11-03. This is a code and local-test review, not a new hardware test.

## Findings, in severity order

No high- or medium-severity defects found.

1. **Low — stale add-on image version label (fixed).** `addon/Dockerfile` still defaulted `BUILD_VERSION` to `0.2.1`. Local builds and the container CI job omit that argument, so their `io.hass.version` label would misidentify the 0.3.1 application. Tagged release builds already override the argument correctly. Updated the default to `0.3.1`, extended the existing release-version regression test, and added the Dockerfile to the contributor version checklist. The regression assertion failed with the old default and passed after the correction. Both changelogs now describe this correction.

## BUG 10 and MQTT publish paths

`Store._publish_meter()` is the only production caller of `publisher.publish()`. Frame processing, calibration commands, read-window expiry and minute/final refresh all use it under the store lock. With neighbourhood collection enabled, it always adds `vs_neighbourhood_today`, including an explicit `None` when comparison data is unavailable. Disabled collection omits the field intentionally.

The existing 16-case regression matrix covers all four paths, enabled/disabled collection and qualified/unqualified cohorts. The expiry case also checks the read-window OFF state. MQTT reconnect and Home Assistant birth replay cached complete states through `Publisher._publish()`; two added tests inspect the actual JSON sent to the client and confirm the comparison survives both reannouncement paths. No further receiver-state correction was needed.

## Timestamps and scan output

The receiver configures one Python logging formatter. The add-on startup script executes the CLI directly, without a second logging wrapper. Existing subprocess tests confirm a single ISO timestamp and the correct process timezone offset in UTC and UTC+10.

Supervisor source review supports the absence of an automatic second prefix in its default view: its app configuration [defaults to plain log formatting](https://github.com/home-assistant/supervisor/blob/main/supervisor/apps/validate.py), and its [plain journal formatter](https://github.com/home-assistant/supervisor/blob/main/supervisor/utils/systemd_journal.py) returns the message unchanged. The downloaded plain formatter was also exercised locally against a receiver-style line and preserved it byte-for-byte. Explicit timestamp/verbose collector views can add their own timestamps. This check did not run a live Supervisor instance.

Two added CLI subprocess tests decode generated synthetic IQ in UTC and UTC+10. Both confirm stdout remains parseable JSON, the frame time remains sample-derived UTC, counts are intact, stderr is empty, and scan mode creates no receiver data directory.

## Versions, changelog and privacy

After the Dockerfile correction, current application, package, add-on, Compose, card and default image-label versions agree at `0.3.1`. Historical feature-introduction and hardware-test versions remain appropriate. The 0.3.1 changelog claims match the reviewed implementation and documentation; both changelog sections include the image-label correction.

The public distributable privacy guard passed. A separate read-only audit extracted 31 actual transmitter IDs from private source frame tables and meter summaries, then checked their decimal and hexadecimal spellings across the distributable tree and added diff lines: zero matching files or added-line matches. Private literals and source data remained outside this repository. Manual review found no new credentials or personal data in the reviewed changes. This does not claim that a generic guard can identify every possible private value or read text embedded in raster pixels; no raster assets changed in the reviewed commits.

## Validation

- Original checkout: 335 Python tests passed on Python 3.13.16.
- Final checkout: 339 Python tests passed, including four added scan/reannouncement cases.
- All 49 Node card tests passed on Node 22.23.3; JavaScript syntax passed.
- Ruff, shell syntax, both installed CLI help commands and `git diff --check` passed.
- `scripts/check_release.py` passed with zero failures; `scripts/prepare_release.py v0.3.1` passed and extracted the intended notes.
- Both root and self-contained add-on layouts built a wheel and source distribution using the pinned build backend. Wheel application/metadata versions and source-distribution requirements were checked.

No Docker/Podman engine, physical RTL-SDR or live HAOS/Supervisor was available for execution here. Container builds, architecture-specific execution and a live Home Assistant session remain unverified by this review. No pushes or tags were made.
