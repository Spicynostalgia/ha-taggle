# Calibration addition — 8 November 2026

Added “How I got 5 litres per pulse” immediately after the walkthrough's
counter-to-water step in the repository, wiki and website editions. The new
narrative is 425 whitespace-separated words excluding its heading, image alt
text and captions. Dan's first-person account covers the rejected hourly fit,
the timing problem, three whole-day checks, the 24-hour utility-reading check,
dial photos, the V100 specification and davidjb's cloud configuration. It ends
with practical calibration guidance and a link to the wiki.

## Evidence and reproduction

- `make_calibration_figures.py --data-dir /projects/taggle-blog-shots/calibration`
  reads all three approved snapshots without writing to them. It shares the
  original figure generator's style/save helpers. All 146 hourly deltas use
  their actual ending timestamps in Australia/Brisbane (UTC+10); missing
  intervals are not invented as zeroes.
- The daily scatter uses `calibration.json`'s three checks and a 5 L/pulse
  reference line. Annotations divide the displayed tenths of a litre, so the
  printed arithmetic agrees. Full-precision ratios remain in provenance.
- The Energy comparison uses `radio_litres` only for 3–6 November: 24 radio
  hours, no filled/pending hours, utility total present. Partial days and
  utility-only backfill are excluded. This later snapshot's utility totals
  remain separately labelled from the earlier calibration checks.
- The third figure reports the rejected/unapplied fit: 3.59 L/pulse,
  R² 0.72, NRMSE 0.66, RMSE 23.53 L, 90 matched / 62 nonzero hours,
  acceptance thresholds and 28.3–28.5% daily errors. No hourly utility series
  is present or fabricated.
- The independent 585 L / 116 pulses = 5.04 L/pulse check, dial-photo agreement,
  register-specific V100 factor and cloud cross-check come from wiki
  `Calibration.md`. They are distinguished from the daily usage checks.
- Source SHA-256 hashes still match. A second run with `--out` in a temporary
  directory reproduced all three PNGs, label files and provenance byte-for-byte.

## Publication checks

- Article text, including code, tables and captions, matches across Markdown,
  wiki and rendered HTML. All 15 PNGs match byte-for-byte in four locations
  (60 copies): repository, wiki, editable site assets and fingerprinted output.
- Privacy self-test passes all 115 private identifier/frame/bit-dump probes,
  plus rendered-label and PNG-metadata rejection. The expanded audit requires
  all eleven matplotlib label files, retains exactly the same two approved IDs
  and selected frames, and finds no forbidden matches. The publication audit
  includes the new generator and provenance; source snapshots remain private.
- Site build fingerprints 53 assets. The verifier passes all 30 HTML pages,
  local links/anchors, metadata, sitemap, FAQ/HowTo parity, CSP and fingerprints.
  The existing homepage transfer budget remains 228,805 B raw / 156,449 B with
  text gzip. The blog sitemap date is already the actual edit date, 2026-11-08.
- Chromium with JavaScript disabled at 1440, 768, 390 and 320 px: all fifteen
  figures decode, no page overflow, all fifteen contents targets exist,
  full-size image links return 200, homepage navigation/footer links work,
  and skip-link/visible keyboard focus checks pass.
- Direct inspection covers all three standalone plots, desktop/phone section
  and figure screenshots, and every screenshot listed by the final inspector.
  The addition uses the existing type, palette, figure presentation and spacing.

## Visual review

Single-section guidance was used; no new design direction or stock imagery was
needed. The scientific plots are original matplotlib output from the approved
meter data. The existing full-size links provide a readable view of dense plot
labels on phones. Captions state the important results and data limitations.

The general marketing-page inspector initially reported seven rule categories
in the incumbent article presentation: back navigation treated as an eyebrow,
actual byte values treated as index numbers, contents/footer rules, existing
figure outlines, headline scale, the static reading experience and the original
three-line phone title. The source linter also flags the actual byte value `01` in the existing frame table; that protocol fact is retained. The final inspector run explicitly allowed these categories to
preserve the requested existing post style: zero remaining failures at 1440,
768 and 390 px. Its one video warning is accepted because this addition is a
static data analysis and the approved sources contain no video. This is a scoped
content addition, not a claim that the existing article passes those marketing
style rules without allowances.

Visual critique: design 7/10, usability 8/10, creativity 6/10, content 9/10;
weighted score 7.3/10. The plots and prose form a clear evidence sequence with
consistent margins and no collisions. Remaining limitation: figure annotations
need the full-size view on narrow phones. No sample data or placeholders were
introduced. Existing unrelated logo work and untracked briefs/reports are
excluded from commits. Nothing was pushed or deployed.
