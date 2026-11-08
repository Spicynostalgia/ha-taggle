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
  /path/to/site/site/blog
```

The expected archive has `captures/iq-922200k-g40-3900s.cu8`, the matching
`analysis/live/full-frames.jsonl`, and measured survey bins in `analysis/bins.csv`.
Those inputs are not distributed. The generator seeks into the IQ file and
reads only 1.2 seconds; it does not load the complete recording. It independently
acquires that slice, runs the current decoder, reruns Viterbi and both CRCs,
then verifies the result against the archived frame. The encrypted record's
outer framing is also checked. The production CLI runs against a temporary copy
of the same slice in scan mode; no meter IDs are configured, MQTT is not used,
and private stdout remains in memory until its ID and timestamp are redacted.

| PNG | Evidence shown |
| --- | --- |
| `01-band-occupancy.png` | Measured 915–928 MHz survey occupancy and actual burst spectrum |
| `02-single-burst.png` | Actual spectrogram and 0.5 ms average power envelope |
| `03-pn-correlation.png` | Measured template versus generated 4095-chip partial-band PN model |
| `04-bpsk-constellation.png` | Real despread projections before and after residual carrier/phase correction |
| `05-fec-and-crcs.png` | Actual Viterbi result, zero corrections, both CRC-8 checks passing |
| `06-clear-frame.png` | Real redacted 18-byte frame with field boundaries and detached illustrative arithmetic |
| `07-encrypted-frame.png` | Real redacted 24-byte record, checked clear framing and opaque body |
| `08-receiver-log.png` | Actual production CLI output after privacy masking |

The frame figure masks all ID nibbles, usage counters, unknown fields and CRC
values, including fields crossing byte boundaries. Only sync, format and known
flag positions remain visible in the hex display. The encrypted body is
withheld rather than published as ciphertext. Counter values `120, 110, 104`
are an explicitly illustrative example, not a captured household's readings.

The audit builds private grep patterns from every recorded decimal and hex ID,
as well as full raw frames and coded dumps. It checks all supplied text files,
eight rendered-label sources and PNG textual metadata without printing matches.
Wiki and site image copies must be byte-identical to these audited originals;
site fingerprinting changes filenames only. Pass any additional changed HTML,
CSS, generated manifests or reports to `--paths` for the final publication audit.
