# Blog validation — 8 November 2026

## Author’s approved sample — current revision

- All clear figures now use the author’s own 18-byte frame, ID 527814 / 0x80DC6,
  at recording offset 595.33 seconds. The first 1.2 seconds of the archived
  `burst06_595.33s.cu8` clip are read; captures and analysis inputs stay unchanged.
- The recovered full frame matches the archive exactly. Viterbi corrects zero
  bits, forward encoding matches all 288 coded bits, and sync, zero tail and both
  CRC-8 checks pass. Counters are 46234, 46223, 46218, yielding deltas 11 and 5.
- The real production CLI runs in scan mode with only the author’s ID configured.
  It emits that ID and those counters, without MQTT or persistent state writes.
  Timestamp is omitted. Replay SNR is 30.9 dB; archived SNR is 30.7 dB.
- Full decoded hex, ID and counters are shown with the author’s permission for
  this post only. Neighbours’ IDs, checksums and encrypted body remain masked.
  The encrypted example still passes outer framing checks without usage decoding.
- `check_privacy.py` exempts only the author’s decimal/hex ID and this exact decoded
  frame. All coded/on-air dumps remain forbidden. `test_privacy.py` accepts the
  approved example and rejects 118 private ID/frame/bit-dump probes, plus private
  rendered labels and PNG metadata, without printing private values.
- The article is 1,653 whitespace-separated words; pitch body is 169 words.
  All three editions have identical article text and byte-identical copies of
  all eight PNGs. Site build and verifier pass: 30 HTML pages, 46 fingerprinted
  assets; homepage budget remains 227,913 bytes raw / 156,235 bytes with text gzip.
- Publication privacy audit includes all three editions, 32 PNG copies, eight
  rendered-label sources, scripts, pitch, provenance, manifest and validation
  reports. It finds zero forbidden matches across 15 private IDs in 20 frames.
- Browser checks pass at 1440, 768, 390 and 320 px with JavaScript disabled:
  all eight images decode, no horizontal overflow, full-size and contents links
  work, skip link and visible keyboard focus pass. Direct PNG inspection confirms
  readable full hex, ID, counters and receiver output. Whitespace checks pass in
  all three repos. Commits are local only. No push, deployment or email is part of this revision.

## Earlier publication checks (before the approved-sample change)

The revised article is 1,590 whitespace-separated words including captions, links
and screenshot placeholders. The draft pitch body is 145 words. Nothing was pushed, deployed
or emailed. The source capture, research archive and decoder are read-only.

## Scientific checks

- Read only a 1.2-second slice of the 922.2 MHz, 2.4 MS/s recording.
- Acquired the slice with the production PN/carrier detector, then reused its
  DSSS recovery and frame decoder. Recovered bytes match the archived record.
- Explicit Viterbi decode: zero corrected coded bits; forward re-encoding matches
  all 288 captured coded bits. Sync `C0`, zero tail, header CRC-8 and frame CRC-8
  pass. The diagram does not imply the production decoder needed FEC repair.
- The archived 24-byte record also passes the production framing/CRC checks;
  its output contains no counters. Its body is opaque throughout publication.
- The receiver image is actual production CLI stdout from replaying that slice,
  with ID masked and timestamp omitted before rendering. No configured IDs,
  MQTT connection or persistent receiver state/log writes were used.
- Full-band occupancy uses the measured 409-sweep bin summary, distinguished
  from the later confirmed burst. No simultaneous 13 MHz recording is claimed.
- All eight PNGs have matching rendered-label sources. See [FIGURES.md](FIGURES.md)
  and `img/provenance.json` for inputs, reproduction and the decoder commit.

## Text and site checks

- Main and wiki Markdown are identical after changing image paths.
- Site article prose and captions match the rendered Markdown exactly, excluding
  the site's date/read-time metadata and contents navigation.
- All eight wiki, site source and fingerprinted deployed PNG copies are
  byte-identical to the main repository originals.
- `python3 scripts/build.py` and `python3 scripts/verify.py` pass in the site repo:
  30 HTML pages, all local links/anchors, unique metadata/canonicals, sitemap,
  CSP/fingerprints, existing council evidence and FAQ/HowTo parity.
- Site budget excluding logos, including social PNG: 227,913 bytes raw,
  156,235 bytes with text gzip, within the existing 300 KB limit.
- Browser checks cover 1440, 768, 390 and 320 px with JavaScript disabled:
  eight decoded images and working full-size links, contents targets, no
  horizontal overflow, homepage nav/footer link, skip-to-content focus and
  visible keyboard focus. Inline protocol values have non-zero rendered width.
- Site design follows existing Manrope, colors, header and footer. Inline code
  uses weighted Manrope because the incumbent monospace font failed in the
  verification browser. Existing global animation/hover detector warnings were
  checked against actual article usage; the article has no animation.
- Independent site finish review returned **ship**, scoped to the article and
  shared chrome at all four widths, with no material fixes.
- `git diff --check` passes in all three repos. No `docs/` index exists, so no
  index link was added. The main README and unrelated logo edit remain untouched.

## Privacy grep

`check_privacy.py` read all 20 records and built private fixed-string grep
patterns for their 16 unique decimal IDs, matching hexadecimal IDs and complete
raw frame/coded-bit dumps. `rg` reported **zero matches** in publication text,
figure-generation/audit scripts, all eight matplotlib rendered-label sources,
PNG text metadata, copied images, changed site HTML/CSS, and asset manifest.
The initial complete audit covered 83 text/metadata inputs and 32 PNG copies;
the final audit also includes this report and the site validation report.

Every ID shown keeps only its first two decimal digits. All corresponding hex
ID nibbles, absolute counters, unknown fields and checksum values are masked
before plotting. The detached `120, 110, 104` arithmetic example is illustrative.
No raw capture, frame archive, private stdout, precise reception timestamp,
personal contact information or location finer than Gladstone, QLD is included.

The brief referred to datasheet links in `docs/PROTOCOL.md`; that file has none.
We instead located them in the research/wiki sources and verified the actual
SP3C, Cockatoo and V200HT manufacturer PDFs. The article links those directly
and distinguishes their product specifications from the observed radio format.

## Plain-language revision — 8 November 2026

- Rewrote the article and pitch in direct language. Retained every original
  numeric value and external link; reviewed the technical details against the
  original draft. Captions now have one or two sentences.
- Added four comment placeholders: inspectrum waterfall and URH bit view for
  each of a clear and an encrypted burst. No new screenshots were produced here.
- Verified main/wiki Markdown equality after normalising image paths. Compared
  the site article's parsed text against independently rendered Markdown:
  prose and captions match, excluding site metadata and contents navigation.
  All four screenshot comments also match.
- All eight original figures remain unchanged and byte-identical across main,
  wiki, site source and fingerprinted site output. Scientific decoding and
  browser checks above describe the original figure publication; this copy-only
  revision did not rerun those checks.
- Rebuilt the site and reran its verifier: 30 pages pass, with the same transfer
  budget. Sitemap lastmod already matches the content-edit date, 2026-11-08.
- Reran the privacy grep over the revised publication and figure sources:
  16 unique IDs from 20 frames, 51 text/metadata inputs, 32 PNG copies and eight
  rendered-label sources; zero unmasked decimal/hex IDs or raw frame/bit dumps.
- Whitespace checks pass in all three repositories. Only requested publication
  files and this validation record are committed; unrelated work is untouched.
