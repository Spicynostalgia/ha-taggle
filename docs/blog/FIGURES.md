# Figure reproduction and publication scope

The post has eight matplotlib figures and four supplied SIGINT tool images.
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

The generator reads only the first 1.2 seconds of
`captures/bursts/burst06_595.33s.cu8`, independently acquires it and reruns DSSS
recovery, Viterbi, re-encoding, framing and both CRCs. Its decoded bytes must
match the selected archive line exactly. The production CLI runs against a
temporary copy in scan mode, with only Dan’s ID configured, no MQTT connection
and no persistent state writes. Its log omits the timestamp. Archived SNR is
30.7 dB; replay SNR is 30.9 dB. Occupancy uses `analysis/bins.csv`.

The encrypted diagram selects the archive record near 1406.47 seconds by ID
and offset, rather than the first 24-byte record. Its framing is checked without
interpreting ciphertext. The clip filename and screenshot round its time
differently from the fitted sample offset (1406.47828 seconds).

| File | Evidence |
| --- | --- |
| `01-band-occupancy.png` | Survey occupancy and confirmed burst spectrum |
| `02-single-burst.png` | Burst 06 spectrogram and power envelope |
| `03-pn-correlation.png` | Real partial-band template versus generated PN |
| `04-bpsk-constellation.png` | Despread projections before/after phase tracking |
| `05-fec-and-crcs.png` | Viterbi, zero corrections, both CRC checks |
| `06-clear-frame.png` | Dan’s full clear hex, ID and counters |
| `07-encrypted-frame.png` | Burst 08’s full header, ID, checksums and ciphertext |
| `08-receiver-log.png` | Actual production CLI output for Dan’s meter |
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

The privacy audit allows exactly the two IDs above and exactly their selected
decoded/coded/on-air frame dumps. Any other archived frame remains forbidden,
even if its ID is approved. Other recorded IDs in decimal or hex remain
forbidden. The self-test checks approved IDs/dumps, rejects the other real
IDs/dumps, and tests rendered-label and PNG-metadata paths without printing
private matches. The eight label files cover matplotlib text; supplied tool
images also receive direct visual inspection. Wiki/site images must be
byte-identical to the audited originals; site fingerprinting changes names only.
