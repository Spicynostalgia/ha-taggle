# Release check · 0.1.0

Prepared 2026-11-02. This records local evidence and remaining validation work; it does not claim a live hardware release test.

## Provenance and application license

**MIT** for the Python application and dashboard card. The receiver's required dependency chain was traced through the independent streaming receiver, partial-band DSSS routines, PN recurrence generator, convolutional codec and CRC routines. Only those mathematical/receiver functions were selected and refactored. They import NumPy/SciPy and Python standard-library modules; no code from the separately licensed third-party radio decoder or its unrelated protocol path is included or imported.

Application parsing, privacy filtering, persistence, MQTT discovery, calibration CLI and deployment integration were implemented for this repository. The card retains the existing lightweight Home Assistant visual approach but replaces its fixed private entities, location assumptions and private network logic with configurable MQTT entities/device lookup. No private credentials, API endpoints or account-specific helpers were copied.

The GPL-licensed **RTL-SDR Blog driver** is built as a separate executable/library dependency, not incorporated into the Python package. Its license remains applicable to that component. Both Dockerfiles fetch the explicit source revision declared by `RTLSDR_REF` from the public upstream repository and preserve its `COPYING` in the image. The application MIT license does not relicense dependencies or the container as a whole. Other upstream components retain their own licenses.

## Privacy scrub

**PASS: zero matching files in the distributable tree.**

- Enumerated all tracked and untracked nonignored project files, including code, tests, comments, Markdown, examples, manifests, Dockerfiles, card source and distribution.
- Checked the private meter IDs extracted from the read-only source frame tables and meter summaries, their hexadecimal forms, and the forbidden owner, place, portal and private-path terms. Only the audit totals were emitted; private literals were not written into this repository or this report.
- Ran repository guards for private absolute host paths, the forbidden decimal ID families, email addresses, recognizable credential formats and prohibited capture/analysis artifact extensions.
- Confirmed example and fixture IDs are fictional. Tests construct frames and IQ from the project's own PN generator, encoder and CRC implementation. No recorded frames, captures, recovered templates or analysis outputs were copied.
- Sanitized the seed brief. Replaced the initial seed commit so its original sensitive contents are absent from publishable history; expired the obsolete local reflog entries and pruned the unreachable seed objects. The replacement and implementation commits use the neutral project identity.
- Runtime configurations, local data, virtual environments, caches and generated package metadata are ignored. They are not release files. Private literals used for the one-time audit remained outside the repository.

Reproduce the public guard with `python scripts/check_release.py`. For a private audit, supply `--deny-file` pointing to a private newline-separated literal list **outside** the repository. Never commit that list. The public guard complements manual provenance review; it cannot know every possible personal identifier.

## Verification

- **69 Python tests passed locally on Python 3.13**, using the pinned dependencies. Tests cover generated 18/21/24-byte IQ through detection/demodulation/FEC/CRC, noise and unrelated carrier rejection, CRC corruption and excess FEC errors, filtering before writes, scan privacy, sequence/counter wrapping, overlapping history, restart persistence, calibration changes, midnight refresh, corrupt checkpoints, CSV calibration and packaging configuration. Release tests also cover mismatched versions in all three manifests, malformed tags, missing/empty changelog sections, release-note section boundaries, and owner substitution across tracked/untracked distributable files while preserving ignored files and `{arch}`.
- A real Paho client passed a socket-level MQTT 3.1.1 test against an isolated local test broker: discovery, state delivery, reconnect, Home Assistant birth handling and graceful offline publication. No external broker was contacted.
- **Five JavaScript card tests passed**: explicit entities, renamed entities via device registry, missing/unavailable states, escaping/config validation and matching distribution.
- **Ruff passed.** Shell syntax and CLI help checks passed.
- Both root and self-contained add-on Python layouts built a wheel and source distribution successfully.
- Chromium rendered the card with generated readings in light/dark themes at 720 px and 360 px. Checked the history table, stale state, and layout bounds; no overflow or browser errors. The interface detector returned no findings. Preview images stayed outside the repository.
- Both amd64 and aarch64 Home Assistant Debian base-image tags were checked against the public registry and returned valid manifests.
- CI is configured to test Python 3.11/3.13 and build standalone/add-on images for amd64/aarch64, with `push: false`. PRs never publish images.
- The tag-only release workflow validates exact `vMAJOR.MINOR.PATCH` tags against `addon/config.yaml` and both Python manifests before registry login or publication. Local `prepare_release.py v0.1.0` validation and changelog extraction passed.
- Release publishing uses pinned action major versions, QEMU/Buildx and the built-in `GITHUB_TOKEN` with `packages: write` and `contents: write`. Each add-on architecture gets its own versioned GHCR image; standalone version/latest tags contain amd64/arm64 manifests. The GitHub Release is created from the matching root changelog section after all image builds succeed.
- `scripts/set_owner.py` configures the literal `GITHUB_OWNER` placeholder once across distributable files. The add-on keeps Home Assistant's `{arch}` substitution; Compose defaults to GHCR and includes a commented local-build option. README and CONTRIBUTING document setup and public package visibility.

## Remaining validation

No Docker/Podman engine or physical RTL-SDR is available in this workspace. **Container builds, Blog V4 USB reception, HAOS/Supervisor installation and a live Home Assistant Energy session were not run locally.** The build-only CI and tag-release workflows have been authored but cannot be claimed as passed until they run on a published repository. GHCR pushes, multi-arch manifests and GitHub Release creation have not been exercised here; release tests validate local preparation only. Python 3.11 execution is covered by the configured CI matrix, not a local run.

The card was checked in Chromium with representative Home Assistant states; it was not loaded into a live Home Assistant instance. Encrypted payloads remain opaque. Real-world RF range, counter-reset behavior, unit calibration and compatibility with other transmitter variants need own-meter verification.

No git remote was added and nothing was pushed. All changes are committed locally with a neutral project identity. Replacing the image owner placeholder, publishing the repository and a version tag, making the three GHCR packages public after their first publication, adding the add-on repository URL, and HACS installation remain owner actions. The tag workflow automates image publication and GitHub Release creation once triggered.
