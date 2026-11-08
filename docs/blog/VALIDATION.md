# Blog validation — 8 November 2026

The article is 2,145 whitespace-separated words including captions and links.
The draft pitch body is approximately 151 words. Nothing was pushed, deployed
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
