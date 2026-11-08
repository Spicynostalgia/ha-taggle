# SDR walkthrough style pass — 8 November 2026

Applied BRIEF-style.md to the repository, wiki and website editions, plus the
rtl-sdr.com pitch. The article now opens with three motivation sentences, a
one-paragraph TL;DR and the real receiver replay screenshot. The walkthrough
keeps the radio-to-counter sequence, with dense calculations and conventions
in “Details for the curious” blocks or the existing tables. All fifteen figures
have prose introductions and italic captions, numbered in reading order.
The calibration narrative and no-decryption policy remain. Open questions cover
unknown flags, a production 21-byte field test and other councils, followed by a
results invitation and the fork instructions.

The live RTL-SDR pipeline and scan/normal-mode commands match the existing wiki
Python CLI documentation verbatim. No acquisition flags were invented. The
pitch body is 165 whitespace-separated words after resolving Markdown links,
excluding subject, salutation, sign-off, image picks and link list. Its stale
count of twelve images was corrected to the current fifteen.

Validation completed:

- Original inline code strings, numeric tokens (apart from figure numbering),
  image references and external links are retained. Both tables are unchanged.
  Manual review checked the relocated technical detail and calibration account.
- Rendered article text, tables, code and captions match across all three
  editions. All fifteen PNGs match in the repo, wiki, editable site assets and
  fingerprinted site output: 60 copies. Calibration source hashes, displayed
  ratios and complete-day overlap checks still pass.
- Privacy self-test passes both permitted examples and all 115 private
  ID/frame/bit-dump rejection probes, plus rendered-label and PNG-metadata
  rejection. Publication audit passes all 89 text/metadata inputs, 60 PNGs and
  eleven label sources, with zero forbidden matches across 14 private IDs from
  20 archived frames. Source recordings and snapshots were not changed.
- Site build fingerprints 53 assets. The site verifier passes all 30 HTML pages,
  local links/anchors, metadata, FAQ/HowTo parity, council evidence, crawler
  files, CSP and fingerprints. Homepage transfer budget is unchanged:
  228,805 bytes raw / 156,449 bytes with text gzip, below 300 KB.
- Chromium with JavaScript disabled at 1440, 768, 390 and 320 px passes fifteen
  loaded figures, matching full-size image links returning HTTP 200, fifteen
  italic captions, nine detail blocks, sixteen contents targets and no page
  overflow. Table regions remain within the viewport. Homepage navigation,
  skip link, contents navigation and visible keyboard focus pass.
- Direct screenshot inspection covered desktop/phone openings, phone CRC
  details and the phone open-questions section. The site keeps its existing
  CSS and assets; the opening screenshot loads eagerly.
- `git diff --check` passes in all three repositories.

No RF behavior or compatibility claims were added. Existing unrelated logo
changes, briefs and reports are excluded from these commits. Nothing was sent,
pushed or deployed.
