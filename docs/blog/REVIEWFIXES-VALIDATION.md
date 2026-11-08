# Fresh-eyes review fixes — 8 November 2026

Applied `BRIEF-reviewfixes.md` against the eleven findings in the separate
review checkout. Dan's first-person voice, calibration section and existing
presentation are retained. The repository article, wiki article, rendered site
and draft pitch are updated. Nothing was pushed, deployed or emailed.

## Corrections

- Finding 1: kept the generator link on `main`, as the brief directs.
- Findings 2/5/6: copied the three corrected tool screenshots from
  `/projects/taggle-blog-shots/`, regenerated all eight radio figures and
  refreshed provenance. Figure 07 now says “No keys available; body not
  interpreted”. Captions describe the opaque body and length-based encrypted
  classification. The qualified manufacturer AES-128 discussion remains.
  The text distinguishes the 0.45-second marked window from the 0.416-second
  frame, and expected rectangular-chip null-to-null width from measured RF
  bandwidth. Nominal ADC-clock assumptions are explicit.
- Findings 3/10: corrected long-gap recovery versus inconsistent sequences,
  and described the Costas detector's complex-symbol squaring accurately.
- Findings 4/8: documented default neighbourhood processing, explicitly set
  `neighbourhood` and `log_all_meters` false for own-meter use, disclosed other
  IDs in scan output, and gave the fixed target, accepted centre range and
  acquisition search radius. The runnable scan uses existing CLI flags and
  links installation instructions. Its waiting period is not a guarantee.
- Finding 7: explained the squared-BPSK carrier screen and known-PN check,
  defined chip/PN, and separated earlier polynomial recovery from this replay.
- Finding 9: retained numeric `meter_id` in the real CLI excerpt, disclosed
  JSON reformatting/timestamp omission, and removed the abbreviated command
  from the image.
- Finding 11: documented exact private-data requirements, adaptation for other
  recordings, supplied-image hashing versus GUI reproduction, and visible
  tool settings. Added `verify_bits.py` with the two approved captured on-air
  bitstreams; it requires no private IQ or archive and states its RF limits.

## Verification

- `make_figures.py` successfully reacquired the bounded real clear-IQ slice,
  recovered the archive bytes, reran Viterbi and exact re-encoding, checked
  framing/CRCs for both selected captures and replayed the production CLI.
  Numeric ID, counters and RF measurements match the real replay. The source
  slice hash is unchanged. Its decoder commit is recorded in provenance;
  receiver source is unchanged from the reviewed decoder commit.
- `verify_bits.py` passes for both approved streams: zero Viterbi corrections,
  exact re-encoding, preamble/sync/tail and both CRCs. Clear counters, flags,
  sequence and pulse/litre differences pass; the opaque body is not interpreted.
- The three corrected tool PNGs match the supplied source files byte-for-byte
  and match their refreshed provenance hashes. Direct visual inspection covered
  those three images, the clear URH settings, and both regenerated diagrams.
- Article text matches across repository, wiki and rendered HTML. All fifteen
  figures match across all sixty repository/wiki/site-source/site-output copies.
  Calibration source hashes and computed daily ratios remain valid.
- Site `scripts/build.py` fingerprints 53 assets; `scripts/verify.py` passes
  all 30 pages, links, metadata, structured data, CSP and fingerprints. The
  homepage remains below its 300 KB transfer budget.
- Chromium at 1440, 768, 390 and 320 px, JavaScript disabled: fifteen loaded
  figures and full-size links, sixteen contents targets, nine details blocks,
  no page overflow, working homepage navigation, skip link and keyboard focus.
  Desktop and phone screenshots were inspected after font rendering settled.
- Three existing focused tests pass: long-gap interval recovery, scan config
  and RTL arguments, and file scanning without MQTT or persistent writes.
- Privacy self-test accepts both approved captures and rejects all 115 private
  ID/frame/bit-dump probes plus rendered-label and PNG-metadata probes. The
  publication audit covers all three editions, pitch, public example, scripts,
  provenance, validation reports and sixty PNG copies with zero forbidden
  matches across fourteen private IDs from twenty archive frames. Only IDs
  527814 / 0x80DC6 and 766910 / 0xBB3BE and their selected captures are permitted.
- `git diff --check` passes in all three repositories. Unrelated logo edits,
  briefs and earlier untracked reports are excluded from these commits.

Reproduction commands and limitations are in [FIGURES.md](FIGURES.md).
