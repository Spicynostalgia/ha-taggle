# Contributing

Keep changes focused on receiving supported Taggle meters and integrating their observations with Home Assistant. Use Python 3.11–3.13 and install development dependencies with `pip install -e '.[dev]'`.

Before submitting, run `ruff check .`, `pytest -q`, `node --test tests/card.test.cjs` and `python scripts/check_release.py`. Container changes should build both `docker/Dockerfile` from the repository root and `addon/Dockerfile` from `addon/` on amd64/aarch64. CI builds images without publishing them.

Never submit personal information, real meter IDs, credentials, private host paths, captures, recorded frames or private analysis artifacts. Generate reproducible fake test data using `tests/synthetic.py`. Do not add unrelated radio decoders, portal scraping, decryption or key-search functionality.

The frontend is dependency-free. Edit `card/taggle-card.js`, then copy it to `dist/taggle-card.js`; the checks require byte-for-byte equality. Test light/dark themes, narrow widths, missing entities, renamed entities and keyboard-accessible history.

Explain changed behavior, compatibility implications and validation in your pull request. Contributions are under the repository's MIT license; preserve third-party dependency licenses and document provenance when incorporating code.

## Publishing

Before publishing your fork, run `python scripts/set_owner.py your-github-name` and commit the substitutions. `GITHUB_OWNER` is a literal placeholder, replaced everywhere with your lowercase GitHub user or organization. The add-on `image` must point at `ghcr.io/GITHUB_OWNER/ha-taggle-addon-{arch}` with the owner replaced; preserve `{arch}` for Home Assistant. Compose uses the standalone GHCR image and retains a commented local-build block.

Update versions together in `addon/config.yaml`, `pyproject.toml` and `addon/pyproject.toml`, and maintain both changelogs. Run `python scripts/prepare_release.py v<version> --notes /tmp/taggle-release-notes.md` before tagging. Tags `v*.*.*` trigger the release workflow, which requires an exact `vMAJOR.MINOR.PATCH` match and a nonempty matching root changelog section. It publishes both add-on architectures and the standalone multi-arch version/latest images with the built-in `GITHUB_TOKEN`, then creates a GitHub Release from that section. No personal access token is needed. Make the GHCR packages public after their first publication; PR CI continues to build without publishing. See README [Publishing](README.md#publishing).
