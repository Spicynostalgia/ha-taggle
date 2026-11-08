# Figure reproduction and privacy

The eight PNGs are matplotlib renders from private, read-only radio observations.
They are 1600 pixels wide and intended to remain legible when displayed at
800 pixels. Each `.labels.json` file records the exact strings rendered in its
PNG, including axis labels, for the privacy audit. These are publication-safe
labels, not raw decoded data. `img/provenance.json` identifies the bounded IQ
slice by SHA-256 and records the decoder commit and successful checks.

Use Python with `numpy`, `scipy`, `matplotlib`, `paho-mqtt` and `Pillow` installed,
and `rg` on PATH. The decoder supplies the DSP, coding and production CLI.

```sh
OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 python docs/blog/make_figures.py \
  --captures /path/to/private/captures \
  --analysis /path/to/private/analysis \
  --decoder /path/to/ha-taggle

python docs/blog/check_privacy.py \
  --frames /path/to/private/analysis/live/full-frames.jsonl \
  --paths docs/blog /path/to/wiki/Blog-Decoding-Taggle.md \
  /path/to/wiki/images/blog /path/to/site/src/assets/blog \
  /path/to/site/site/blog /path/to/site/site/assets/blog
```

To check that the exception stays narrow:

```sh
python docs/blog/test_privacy.py --frames /path/to/private/analysis/live/full-frames.jsonl
```

The expected archive has `captures/bursts/burst06_595.33s.cu8`, the matching
`analysis/live/full-frames.jsonl`, and measured survey bins in `analysis/bins.csv`.
Those inputs are not distributed. The generator reads the first 1.2 seconds of that clip; it does not load the complete recording. It independently
acquires that slice, runs the current decoder, reruns Viterbi and both CRCs,
then verifies the result against the archived frame. The encrypted record's
outer framing is also checked. The production CLI runs against a temporary copy
of the same slice in scan mode, with only the author’s ID configured. MQTT is
not used, no persistent state is written and the timestamp is omitted.

| PNG | Evidence shown |
| --- | --- |
| `01-band-occupancy.png` | Measured 915–928 MHz survey occupancy and actual burst spectrum |
| `02-single-burst.png` | Actual spectrogram and 0.5 ms average power envelope |
| `03-pn-correlation.png` | Measured template versus generated 4095-chip partial-band PN model |
| `04-bpsk-constellation.png` | Real despread projections before and after residual carrier/phase correction |
| `05-fec-and-crcs.png` | Actual Viterbi result, zero corrections, both CRC-8 checks passing |
| `06-clear-frame.png` | Author’s unmasked 18-byte frame with field boundaries and measured counter deltas |
| `07-encrypted-frame.png` | Real redacted 24-byte record, checked clear framing and opaque body |
| `08-receiver-log.png` | Actual production CLI output with author’s ID and counters; timestamp omitted |

The clear sample is the author’s own meter, 527814 / 0x80DC6, shown with his
permission for this post only. It is the 18-byte record at sample offset / 2.4e6
= 595.33 seconds, archived SNR 30.7 dB. Its full decoded hex and measured counters
46234, 46223, 46218 are visible. The replay reports SNR 30.9 dB; acquisition and
tracking are rerun on the bounded clip, rather than copied from archive diagnostics.
All other IDs stay masked. The encrypted example masks its ID nibbles, counters,
unknown fields and CRCs, and withholds its body rather than publishing ciphertext.

The audit exempts exactly decimal ID 527814 and hex ID 0x80DC6, plus this one
approved decoded frame. It still forbids other recorded IDs, other complete
frames and every coded/on-air bit dump, including the author’s. It checks all
supplied text files, eight rendered-label sources and PNG textual metadata
without printing private matches.
Wiki and site image copies must be byte-identical to these audited originals;
site fingerprinting changes filenames only. Pass any additional changed HTML,
CSS, generated manifests or reports to `--paths` for the final publication audit.
