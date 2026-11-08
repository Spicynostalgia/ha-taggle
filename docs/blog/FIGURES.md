# Figure reproduction and publication scope

The post has eleven matplotlib figures (eight radio-analysis figures and three
calibration figures) and four supplied SIGINT tool images.
Every published image is unblurred. Dan’s own clear burst 06 is ID 527814 /
0x80DC6. The encrypted example is burst 08, ID 766910 / 0xBB3BE, matching both
supplied encrypted screenshots. No neighbours’ clear frames or usage appear.

The matplotlib PNGs are 1600 pixels wide. Each `.labels.json` records all
rendered strings, including axis labels, for the privacy audit. PNG textual
metadata is checked too. `img/provenance.json` records the bounded clear-IQ
slice hash, decoder commit, selected frames, RF diagnostics and screenshot
hashes. The source IQ, research archive and reference decoder are read-only.

Use Python with `numpy`, `scipy`, `matplotlib`, `paho-mqtt` and `Pillow`, plus
`rg` on PATH:

```sh
OPENBLAS_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1 python docs/blog/make_figures.py \
  --captures /path/to/private/captures \
  --analysis /path/to/private/analysis --decoder /path/to/ha-taggle

python docs/blog/test_privacy.py --frames /path/to/private/analysis/live/full-frames.jsonl

python docs/blog/check_privacy.py \
  --frames /path/to/private/analysis/live/full-frames.jsonl \
  --paths docs/blog /path/to/wiki/Blog-Decoding-Taggle.md \
  /path/to/wiki/images/blog /path/to/site/src/assets/blog \
  /path/to/site/site/blog /path/to/site/site/assets/blog \
  /path/to/site/src/styles.css /path/to/site/scripts/asset-manifest.json \
  /path/to/site/reports/blog-2026-11-08.md
```

Generate the calibration figures separately from the read-only snapshots:

```sh
python docs/blog/make_calibration_figures.py --data-dir /path/to/private/calibration
```

This sibling generator uses the same style and save helper as `make_figures.py`.
It reads `dan_hours.json`, `calibration.json` and `energy_status.json` without
modifying them. `--out` optionally selects another output folder.
`img/calibration-provenance.json` records source hashes, full-precision daily
ratios, the complete-overlap filter and output hashes. Source snapshots stay
private. Its three PNGs and label files are additional to the original eight.

`09-calibration-hours.png` plots the 146 observed hourly deltas at their actual
ending times in `Australia/Brisbane` (UTC+10), with morning/evening shading.
Missing intervals are not resampled or filled with zeroes.
`10-calibration-days.png` compares the three saved daily checks against
`litres = 5 × pulses`. Annotation arithmetic uses the displayed litres rounded
to 0.1 L before dividing, giving 1082.7/216 = 5.01, 895.0/179 = 5.00 and
680.7/136 = 5.01 L/pulse. The full-precision last ratio is 5.004985…; the
annotation deliberately describes the displayed tenths, not extra precision.
The lower panel uses the later Energy snapshot's separately reported totals:
only 3–6 November have 24 radio hours, zero filled/pending hours and utility
data. It uses `radio_litres`, never the combined `litres` value that can include
utility backfill. No utility-only history or incomplete day is plotted.
`11-calibration-hourly-fit.png` is a statistics panel for the stored rejected,
unapplied zero-intercept hourly fit. No hourly utility observations are supplied,
so no hourly scatter or inferred sub-day utility profile is generated.

Exact reproduction of the eight radio figures requires the original private
dataset, not just any authorised recording. The generator hard-codes both
approved IDs, their recording offsets and expected decode values; it also needs
the original `analysis/bins.csv` and `analysis/live/full-frames.jsonl`. Adapt
those selections, checks and plot annotations for a different capture, and audit
its publication permissions separately. No private input files are distributed.

The radio generator reads only the first 1.2 seconds of
`captures/bursts/burst06_595.33s.cu8`, independently acquires it and reruns DSSS
recovery, Viterbi, re-encoding, framing and both CRCs. Its decoded bytes must
match the selected archive line exactly. The production CLI runs against a
temporary copy in scan mode, with only Dan’s ID configured, no MQTT connection
and no persistent state writes. Its log omits the timestamp and reformats the
JSON while retaining the CLI's numeric `meter_id` type. The screenshot is an
excerpt, without an abbreviated command presented as runnable. Archived SNR is
30.7 dB; replay SNR is 30.9 dB. Occupancy uses `analysis/bins.csv`.

The encrypted diagram selects the archive record near 1406.47 seconds by ID
and offset, rather than the first 24-byte record. Its framing is checked without
interpreting the opaque body, classified as encrypted by the 24-byte length.
The clip filename and screenshot round its time
differently from the fitted sample offset (1406.47828 seconds).

| File | Evidence |
| --- | --- |
| `01-band-occupancy.png` | Survey occupancy and confirmed burst spectrum |
| `02-single-burst.png` | Burst 06 spectrogram and power envelope |
| `03-pn-correlation.png` | Real partial-band template versus generated PN |
| `04-bpsk-constellation.png` | Despread projections before/after phase tracking |
| `05-fec-and-crcs.png` | Viterbi, zero corrections, both CRC checks |
| `06-clear-frame.png` | Dan’s full clear hex, ID and counters |
| `07-encrypted-frame.png` | Burst 08’s full header, ID, checksums and opaque body, classified as encrypted |
| `08-receiver-log.png` | Reformatted production CLI output for Dan’s meter; numeric ID, timestamp omitted |
| `waterfall-clear-burst06.png` | inspectrum, real clear IQ, full receiver band and MHz/time axes |
| `urh-clear-burst06.png` | Universal Radio Hacker PSK, real clear despread symbols, full bits |
| `waterfall-encrypted-burst08.png` | inspectrum, real encrypted IQ, full receiver band and MHz/time axes |
| `urh-encrypted-burst08.png` | Universal Radio Hacker PSK, real encrypted despread symbols, full bits |

The four supplied screenshots are copied byte-for-byte from the task’s
`/projects/taggle-blog-shots/` folder. The clear URH original is named
`urh-clear-burst06-unblurred.png`; publication drops `-unblurred`. Both URH inputs
are the decoder’s despread symbol streams at 20 samples per symbol, not raw RF.
They do not change the ADC sample rate or add missing RF bandwidth. The tool
screenshots are supplied artifacts; `make_figures.py` regenerates the eight
matplotlib figures and hashes the supplied screenshots already in its output
folder. No screenshot is masked, blurred or recreated by the generator.

The supplied inspectrum views show cu8 input at 2.4 MS/s, centred at 922.2 MHz;
annotations add absolute MHz and time since clip start. The clear clip starts
at 594.83 s and the opaque-frame clip at 1405.97 s. The latter rectangle marks
about 0.45 s; its 488 active symbols last about 0.416 s. The 2.4 MHz slice does
not measure full transmitter bandwidth: about 9.6 MHz is an expected unfiltered
null-to-null width only under a rectangular-chip assumption and nominal ADC
clock. The original inspectrum FFT/window/export and annotation steps were not
supplied as a repeatable script.

Both URH views visibly use PSK, one bit per symbol, 20 samples per symbol,
centre 0, noise threshold 0.0354 and a moving-average display filter; the shown
error tolerances are 5 (clear) and 1 (opaque). They show a constant
104-symbol preamble followed by coded bits. The source is the decoder's
despread symbol stream expanded to 20 samples per symbol. A complete original
symbol-export command and GUI project were not supplied, so these settings
document the provided views rather than independently reproducing them. PNG
hashes establish faithful copying, not the original GUI/export process.

For a public check without any private inputs, install the receiver's NumPy
dependency and run from this repository:

```sh
python docs/blog/verify_bits.py
```

`--decoder /path/to/ha-taggle` optionally selects another receiver checkout.
This example embeds the two approved captured on-air bitstreams, packed
MSB-first with explicit symbol counts. It verifies production decoding,
explicit Viterbi decoding with zero corrections, exact re-encoding, preamble,
sync, tail, both CRCs and the clear counters/deltas. It never interprets the
opaque body. It tests bits to fields only, without RF acquisition, timing,
carrier estimation, calibration evidence or screenshot reproduction.

The privacy audit allows exactly the two IDs above and exactly their selected
decoded/coded/on-air frame dumps. Any other archived frame remains forbidden,
even if its ID is approved. Other recorded IDs in decimal or hex remain
forbidden. The self-test checks approved IDs/dumps, rejects the other real
IDs/dumps, and tests rendered-label and PNG-metadata paths without printing
private matches. The eleven label files cover matplotlib text; supplied tool
images also receive direct visual inspection. Wiki/site images must be
byte-identical to the audited originals; site fingerprinting changes names only.
