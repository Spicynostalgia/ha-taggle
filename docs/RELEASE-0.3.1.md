# 0.3.1 soak follow-up audit

The numbered findings and README/AFTER notes were checked against this checkout. Examples and regression tests use fictional transmitter IDs; private soak logs were not copied into the repository.

| Finding | Result |
| --- | --- |
| 1. Add-on list versus Docker mapping for `litres_per_count` | Already documented together in [Calibration](CALIBRATION.md#apply-the-verified-factor), including where each fragment belongs. |
| 2. Beginner Docker/MQTT setup and broker host | Already covered in the README: authenticated Mosquitto Compose example, broker LAN address, container `localhost` caveat and HA installation prerequisite. |
| 3. Fresh `/local/` 404 | Already covered: create HA's `www`, restart HA on first creation, then verify the raw card URL. |
| 4. Fresh card looks broken | Already fixed: neutral first-reading message; previously heard meters retain outage warnings. Covered by card tests. |
| 5. Silent startup | Already fixed: MQTT connection, receiver startup and 15-minute listening messages. Covered by `test_config_mqtt_calibrate.py` and `test_store.py`. |
| 6. Scan timestamps | Already fixed: sample-derived UTC time and rounded signal values, covered by `test_store.py`. Normal receiver logs now also carry ISO local timestamps and offsets, tested in UTC and UTC+10 by `test_cli.py`. |
| 7. HA MQTT integration step | Already present in both add-on and Docker installation instructions. |
| 8. Signal display precision | Already fixed in MQTT discovery and published values, covered by `test_config_mqtt_calibrate.py`. |
| 9. Missing SDR retry spam | Already fixed: 2–60 second backoff, actionable USB/passthrough hint, ten-minute reminder limit. Backoff tests already present; corrected the add-on help's stale two-second-only description. |
| 10. Comparison disappears after dial entry/window expiry | Fixed with one complete meter-publish helper shared by frame, refresh, dial command and window-expiry paths. Regression tests cover all four, with qualified/unknown cohorts and collection enabled/disabled. |

The README TODO and AFTER implementation notes were already addressed: prominent pulse-counter/unknown-offset explanation; manual guided calibration and dial illustration; next-transmission estimates; photo times submitted together with readings; advanced utility automation kept in the calibration reference; previous-day clock-time handling; last-ten-reading attributes; updated standard pulse sizes including 1000 L; V100 specification, pulse-size table and supporting cloud-MQTT reference; encryption caveats; and the empty external-radio-report compatibility list. The current three-step one-hour routine and combined reading/time control supersede the earlier four-step and separate-time-control proposals. Existing calibration and card tests exercise these implemented behaviours.

This release adds README/add-on guidance for the expected several-hour neighbourhood wait after midnight, the interval-end date rule (23:39–00:39 belongs to the new day), and drifting transmit minutes. The calibration guide now also correctly distinguishes 200 privately stored readings from the last ten exposed in HA attributes. Midnight accounting and transmission prediction behaviour are unchanged.

Receiver/package/add-on/Compose/card versions and release instructions are aligned to 0.3.1, with both changelogs updated. Historical feature-introduction and hardware-test versions remain intact. A release regression test checks the current manifests, receiver version, card version, Compose tag and changelog sections together.

Validation on Python 3.13: **335 Python tests passed**, **49 Node card tests passed**, Ruff and JavaScript syntax checks passed, release preparation for `v0.3.1` passed, the distributable privacy guard reported zero failures, and the root Python source distribution and wheel built successfully. The new comparison and timestamp tests were also run before the fixes and reproduced the reported failures.

The notes' physical dongle transfer, further live calibration/photos, external wiki edits and separate website deployment are outside this checkout. No new hardware validation, publication, push or tag is claimed here.
