# Contributing

Keep changes focused on receiving supported Taggle meters and integrating their observations with Home Assistant. Use **Python 3.11–3.13**. From the repository root, create a virtual environment and install development dependencies:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

On Debian/Ubuntu, install `git` and `python3-venv` first if absent. Run Linux commands on the receiver/development host. If you copy [config.example.json](config.example.json) for local testing, protect the copy with `chmod 600 config.json` before adding broker credentials.

Before submitting, run:

```sh
ruff check .
PYTHONPATH=addon python -m pytest -q
node --check card/taggle-card.js
node tests/card.test.cjs
python scripts/check_release.py
python scripts/prepare_release.py v0.3.0 --notes /tmp/taggle-release-notes.md
python -m build --outdir /tmp/taggle-package-check
```

The preparation command checks version alignment, release notes and the Compose image tag; use the intended release version when changing it. Container changes should build both `docker/Dockerfile` from the repository root and `addon/Dockerfile` from `addon/` on amd64/aarch64. CI builds images without publishing them.

Never submit personal information, real transmitter IDs, credentials, private host paths, captures, recorded frames or private analysis artefacts. Use fictional **123456** for documented transmitter IDs and generate reproducible fake test data with [tests/synthetic.py](tests/synthetic.py). Do not add unrelated radio decoders, portal scraping, decryption or key-search functionality. Compatibility beyond the one tested Gladstone/Blog V4 transmitter must remain explicitly unverified until supported by a field report.

The frontend is dependency-free. Edit `card/taggle-card.js`, then copy it to `dist/taggle-card.js`; checks require byte-for-byte equality. Check light/dark themes, narrow widths, missing/renamed entities, calibration status and the possible-leak badge, plus keyboard-accessible history. [The screenshot harness](docs/screenshots/harness.html) uses fictional data. Regenerate its images with `CHROME=/path/to/chromium python scripts/screenshots.py` when the pictured output changes; do not label examples as hardware verification.

Explain changed behaviour, compatibility implications and validation in your pull request. Contributions are under the repository's MIT licence; preserve third-party dependency licences and document provenance when incorporating code.

## Documentation changes

Use Australian English in prose: litres, neighbourhood, behaviour and licence (noun); preserve code keys, URLs and the `LICENSE` filename. Say **transmitter ID**, **USB receiver**, **dial reading** and **litres per pulse**; `litres_per_count` is the setting name. An add-on/app and a HACS dashboard card are separate installations.

The [README](README.md) is the beginner entry point; [add-on help](addon/DOCS.md) keeps the essentials usable inside HA. The [calibration guide](docs/CALIBRATION.md) owns the implemented guided workflow and advanced CSV examples, while [the protocol specification](docs/PROTOCOL.md) owns exact radio/scan details. Link directly to the wiki's [Configuration reference](https://github.com/Spicynostalgia/ha-taggle/wiki/Configuration-Reference), [Entities reference](https://github.com/Spicynostalgia/ha-taggle/wiki/Entities-Reference) and [Neighbourhood comparison](https://github.com/Spicynostalgia/ha-taggle/wiki/Neighbourhood-Comparison) for their extended reference material. Update affected summaries alongside implementation changes.

Check claims against code, not a design proposal. Guided calibration, its controls and the absolute Meter reading are available in **0.3.0**; keep the older **0.2.1** hardware-test record distinct. Manual dial entry is the main calibration route. Do not turn an approximate hint or scan opportunity into an alarm, ownership proof or compatibility guarantee. Check example configuration, MQTT payloads, relative links and heading anchors after editing.

## Reporting issues

Use the [issue forms](https://github.com/Spicynostalgia/ha-taggle/issues/new/choose) for bugs or compatibility reports. Check [Troubleshooting](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting) and [FAQ](https://github.com/Spicynostalgia/ha-taggle/wiki/FAQ) first.

Include your version, installation method, council/utility, USB receiver model and whether usage, ID only, or nothing was heard. Frame length and signal details are optional; **unknown is fine**. Normal scan/INFO output does not expose exact frame length, and missing counts for an unconfigured scan ID do not prove encryption. Do not enable broad logging just to fill that field. Cover transmitter IDs/barcodes in photos, replace quoted IDs with fictional **123456**, redact credentials and private settings, and never include radio captures.

## Confirming compatibility reports

Before adding the `confirmed` label, check that the report describes the reporter's own meter, that the council/state and reception result are clear, and that any photos have transmitter IDs, barcodes, serial numbers and addresses blurred. Remove identifying text or ask for a corrected report before confirming it. Check that **Can we list your council publicly?** is ticked; reports without that consent are excluded from the tables.

Keep the `compatibility` label and add `confirmed` to publish the report in the next automated update. Closed reports still count. Remove either label or uncheck the public-consent box to withdraw a report from the next update. The workflow runs on issue edits/label changes, daily, and via **Run workflow**; it updates the README, [full compatibility table](docs/COMPATIBILITY.md) and badge. Duplicate councils share one row, showing the report count and best result (usage worked, then IDs only, then not received); the other fields come from that same best report.

The seed file [data/compat-seed.json](data/compat-seed.json) preserves the maintainer's Gladstone test. To cite another project's report separately, add an entry with `council`, `state`, `transmitter`, `report: "reported elsewhere"` and `source_url`. These appear under **Reported by other projects**, explicitly untested with ha-taggle, and do not count towards the badge. The optional town/suburb, photos and signal details are never copied into generated tables. Review the generated diff for privacy before publishing.

## Publishing

This checkout already uses image owner **`spicynostalgia`**. In a fork, edit the runtime image references explicitly:

- In `addon/config.yaml`, set `image` to `ghcr.io/<your-lowercase-owner>/ha-taggle-addon-{arch}`. Preserve `{arch}` literally for Home Assistant.
- In `docker-compose.yml`, set `image` to `ghcr.io/<your-lowercase-owner>/ha-taggle:0.3.0` (or your intended release version). Keep this tag aligned with the release.
- Review repository URLs, badges, HACS links and documentation for the fork's owner/repository. Verify the resulting runtime image paths before tagging.

`scripts/set_owner.py` replaces only remaining literal `GITHUB_OWNER` placeholders. It does **not** retarget the already configured `spicynostalgia` image names, even if it reports documentation substitutions. Compose retains a commented local-build block for development.

Update versions together in `addon/config.yaml`, `pyproject.toml`, `addon/pyproject.toml`, `addon/taggle_rx/__init__.py` and the Compose image tag. Maintain both [root](CHANGELOG.md) and [add-on](addon/CHANGELOG.md) changelogs; update README feature requirements and the manual card resource cache suffix too. Run the checks above, including `python scripts/prepare_release.py v<version> --notes /tmp/taggle-release-notes.md`, before tagging.

Tags `v*.*.*` trigger the release workflow, which requires an exact `vMAJOR.MINOR.PATCH` match and a nonempty matching root changelog section. It publishes both add-on architectures and standalone multi-arch version/latest images using the built-in `GITHUB_TOKEN`, then creates a GitHub Release from that section. No personal access token is needed. Make the GHCR packages public after first publication; PR CI continues to build without publishing. [Release workflow details](https://github.com/Spicynostalgia/ha-taggle/wiki/Contributing).
