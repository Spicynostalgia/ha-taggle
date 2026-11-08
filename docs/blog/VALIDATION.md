# Final blog validation — 8 November 2026

The article is 2,754 whitespace-separated words including Markdown table
syntax, code and captions. The draft email body is 166 words. All three editions
have identical article text. Nothing was pushed, deployed or emailed.

## First-person voice revision

- Rewrote the article and captions as Dan describing his own meter and the
  steps from capture to readings. Kept all nine steps and the fork section.
- Added one short linked AI disclosure covering coding and signal analysis;
  the account does not claim manual derivation of the recovered mathematics.
- Rewrote the pitch as a draft from Dan to the rtl-sdr.com editors.
- Compared the revision with its previous commit: every numeric token and
  original link remains, all twelve figures/captions remain, and the exact
  no-decryption policy is preserved. The article is about 6% longer.
- Rebuilt the site and passed its verifier across all 30 pages. Article text
  matches across repo, wiki and rendered site; all twelve images match across
  all four locations (48 copies). No figures needed regeneration.
- Privacy self-test passes: both approved captures accepted; all 115 private
  ID/frame/bit-dump probes plus rendered-label and PNG-metadata probes rejected.
- Publication privacy audit: zero forbidden matches across 14 private IDs from
  20 real frames, 70 text/metadata inputs, 48 PNGs and eight label sources.
- Chromium passes at 1440, 768, 390 and 320 px with JavaScript disabled:
  twelve loaded figures, no page overflow, working contents/full-size links,
  homepage nav/footer links, skip link and visible keyboard focus.
- `git diff --check` passes in all three repositories. Existing unrelated logo
  edits and untracked briefs/reports are excluded from the revision commits.

## Publication changes

- Added the nine-step IQ-to-litres walkthrough with actual archived carrier
  offset, code period, SNR, raw coded hex, bit pairs, encoder polynomials, CRC
  coverage/results, all 18 byte values, flags and unknown fields.
- Dan’s clear burst 06 remains fully visible: ID 527814 / 0x80DC6, counters
  46234, 46223, 46218; deltas 11 and 5 pulses give 55 L and 25 L at the tested
  V100’s 5 L/pulse. Other meters still require calibration.
- Switched the encrypted diagram to burst 08 so it matches the supplied tool
  screenshots: ID 766910 / 0xBB3BE. Full clear header, ciphertext and checksums
  are unmasked. No usage is decoded; no other household’s clear frame appears.
- Replaced all four screenshot placeholders with the supplied inspectrum and
  Universal Radio Hacker images. URH receives real despread symbols at 20 samples
  per symbol, not raw RF. All twelve published images are unblurred.
- Updated the pitch, figure reproduction guide, generator, provenance and
  privacy self-test. The site retains its existing chrome, typography and
  palette, with a native contents list and two accessible table regions.

## Scientific verification

`make_figures.py` read only the first 1.2 seconds of clear burst 06, acquired it
with the production detector, recovered DSSS and BPSK, explicitly ran Viterbi,
and replayed the production CLI. Full decoded bytes match the private archive;
all 288 coded bits match re-encoding. Zero corrections, sync C0, tail 00 and both
CRC checks pass. CLI replay SNR is 30.9 dB; archive SNR is 30.682 dB (30.7 rounded).
No MQTT connection or persistent state writes occur.

The selected encrypted archive record also passes `decode_frame`, explicit
Viterbi, all 384 re-encoded coded-bit comparisons, zero corrections and both
CRCs, without interpreting its opaque body. Its fitted sample offset is
1406.47828 seconds; the clip label rounds differently to 1406.47 seconds.

An independent calculation using the reference `coding.py` and `protocol.py`
checked the walkthrough values:

- Clear first eight coded pairs: `11 10 10 00 11 10 01 11` → `11000000` → C0.
- Header CRC over the 20 ID bits: E4 computed = E4 received; processing ID plus
  CRC gives residue 00. Frame CRC over bytes 1–15: 5D computed = byte 16 (5D).
- Encrypted header CRC: AF computed = AF received; residue 00. Frame CRC: 6A
  computed = byte 22 (6A). Both decoded frames match the selected archive hex.
- Clear fields: sequence 172, flags 1/1/1, counters 46234/46223/46218. Modulo-65536
  deltas, litre conversion and 0.3343-second frame duration match the article.
- The ideal full-code gain is 36.1 dB; the article distinguishes this calculation
  from the measured partial-band correlation SNR.

The SP3C, Cockatoo and V200HT manufacturer PDFs were rechecked for the cited
DSSS/hourly-reporting and encryption claims. They do not identify either captured
transmitter model or establish the encrypted body’s mode or internal fields.

## Parity, build and browser checks

- Main Markdown and wiki Markdown match after substituting image paths. Site
  visible article text, tables, code and captions match the Markdown render.
- All twelve PNGs match byte-for-byte across main, wiki, editable site source
  and fingerprinted deployed assets (48 copies). The supplied screenshots also
  match their task inputs; SHA-256 values are in `img/provenance.json`.
- `python3 scripts/build.py`: 50 fingerprinted assets, obsolete encrypted image
  and stylesheet outputs removed. `python3 scripts/verify.py`: passes all 30
  pages, links/anchors, metadata, sitemap, council evidence, FAQ/HowTo parity,
  crawler files, CSP and fingerprints. Homepage budget: 228,805 bytes raw /
  156,449 bytes with text gzip, below 300 KB.
- Chromium at 1440, 768, 390 and 320 px with JavaScript disabled: all twelve
  images decode, no page overflow, all fourteen contents targets exist, image
  links return full-size originals, homepage nav/footer links work, skip link
  focuses main, visible keyboard focus passes. Both table regions are focusable;
  the comparison table scrolls within its region on small screens.
- Direct visual inspection covers all four supplied tool images, regenerated
  encrypted diagram, desktop article and both tables at desktop/phone widths.
- Impeccable detector ran once. Its wave/glow/stripe findings refer to incumbent
  shared CSS not used on the article; the GitHub-hover warning is superseded by
  the existing explicit white-text hover rule. No new corresponding defect.
- `git diff --check` passes in all three repos. Site build changes on the other
  pages only update the shared stylesheet fingerprint. Existing unrelated logo
  edits and untracked briefs/reports/screenshots are excluded from commits.

## Privacy audit

`check_privacy.py` allows exactly IDs 527814 / 0x80DC6 and 766910 / 0xBB3BE, and
only their two selected decoded/coded/on-air frames. Other frames remain
forbidden even if an ID is allowed. Other recorded IDs, full frame/bit dumps
and other encrypted body dumps remain forbidden.

`test_privacy.py` accepts both selected examples and rejects all 115 private
ID/frame/bit-dump probes, plus a private rendered label and PNG metadata value,
without printing private values. The final publication audit covers all three
editions, rendered-label sources, PNG metadata, scripts, pitch, provenance,
manifest, generated site files and validation reports. It finds zero forbidden
matches across 14 private IDs from 20 real frames. Tool screenshot pixels also
received direct inspection; the text audit does not perform OCR.

Reproduction commands and input requirements are in [FIGURES.md](FIGURES.md).
