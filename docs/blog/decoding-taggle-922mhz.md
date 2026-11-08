# Decoding Taggle water meters at 922 MHz with an RTL-SDR

We wanted hourly water readings from our own meter in Gladstone, QLD, without waiting for a cloud portal. The useful part of that project turned out to be a radio puzzle: a short, noise-like burst near 922 MHz, a repeating spreading sequence, and a small packet carrying more history than we expected.

Using an RTL-SDR Blog V4, we followed that signal through PN acquisition, BPSK demodulation, convolutional decoding and two CRC checks. The result is [ha-taggle](https://github.com/Spicynostalgia/ha-taggle), an MIT-licensed, receive-only decoder that can publish supported clear readings over MQTT into Home Assistant. We also encountered frames whose application data we cannot read. That boundary matters as much as the successful decode.

Only one transmitter has been field-verified against its owner's meter. The mechanical meter is an owner-confirmed Elster (Honeywell) V100; the transmitter's exact model remains unknown. Nothing here establishes that every Taggle installation, council or current transmitter is compatible. Every identifier in this article is masked, and absolute usage counters are withheld.

## Finding the right burst

We began with a 915–928 MHz power survey. Its strongest recurring feature was not automatically our meter. Several signals shared timing, and receiver overload, sidelobes or unrelated transmitters could explain apparent clusters. A busy frequency plot is a list of capture priorities, not a census of water meters.

![Measured survey occupancy across 915–928 MHz, with the later confirmed Taggle channel marked, above a spectrum of the actual decoded burst.](img/01-band-occupancy.png)

*Figure 1. Occupancy is the fraction of observed sweep windows exceeding each bin's temporal median by at least 6 dB, over the available 13.6-minute survey prefix. The lower panel comes from the later confirmed burst. The sweep was frequency-hopped, not a simultaneous 13 MHz IQ recording; its peaks alone do not identify Taggle.*

The useful long recording has a 922.2 MHz centre and 2.4 MS/s unsigned 8-bit interleaved IQ. The decoder targets a carrier near 921.995 MHz, roughly −205 kHz in that recording. Different received bursts have small carrier and clock differences. The current acquisition search is bounded around that expected offset; it does not scan the entire 915–928 MHz band.

Public manufacturer material supplied useful constraints: Byron radio, one-way DSSS, and generally hourly reporting. The [SP3C datasheet](https://taggle.com/wp-content/uploads/2025/12/Datasheet-SP3C-002.pdf), pages 1–2, documents those features. It describes a product family, not the unidentified transmitter on our tested meter. This is DSSS/BPSK, not LoRa or LoRaWAN.

![Actual burst power averaged over half a millisecond and a spectrogram of the same bounded IQ slice.](img/02-single-burst.png)

*Figure 2. A real burst inside a 1.2-second slice, including quiet padding. Power is an uncalibrated ADC measurement, not dBm. The spectrogram shows only the recorded receiver passband.*

The archive's decoded-frame record contains 20 frames: twelve 18-byte clear frames, one 21-byte clear frame and seven 24-byte frames classified as encrypted. Those are recorded observations, not twenty independently validated meter installations. The production project's compatibility claim remains narrower: one field-confirmed 18-byte transmitter; its 21-byte and encrypted receive paths have generated tests only as deployment evidence.

## Recovering a 4095-chip sequence from a partial band

A burst lasts about 0.33–0.42 seconds, depending on frame length. Each coded BPSK symbol is spread with a repeating 4095-chip sequence. The fitted symbol period is near 2046.625 ADC samples, or about 1172.66 coded symbols per second. That implies approximately 4.802 Mchip/s on the nominal sample clock.

There is an important sampling trap here: 2.4 MS/s gives about half a complex sample per chip, not two samples per chip. We captured a filtered portion of the spread signal. Interpolation does not restore the missing RF bandwidth. We therefore compare a predicted *in-band waveform*, derived from the PN sequence, with the measured waveform rather than treating native ADC samples as recovered chips.

Early analysis learned repeating templates without supplying payload bits. Later code recovery identified a degree-12 maximal-length sequence. In the forward recurrence used by the receiver, its polynomial is `x^12 + x^9 + x^6 + x^5 + x^2 + x + 1`, packed as `0x1267`. Starting with register state 1, we output the least significant bit, shift right, and insert the parity of `state & 0x267` at bit 11. Binary one maps to minus one. Cyclic phase and overall BPSK polarity are arbitrary.

The research search matched the recovered template at 0.9752 correlation for the winning primitive polynomial, versus 0.3605 for the runner-up. Those are search diagnostics from the research archive, not sensitivity measurements. The figure below regenerates the known-code comparison from a real capture slice using the receiver's partial-band model.

![Measured cyclic correlation against the regenerated 4095-chip PN sequence, with the acquisition peak annotated.](img/03-pn-correlation.png)

*Figure 3. The measured template is correlated with a filtered, sample-clock-aware PN prediction. The plotted peak is normalised to one; this is neither an ideal full-band PN autocorrelation nor a claim that every chip was sampled.*

The production receiver first screens for a squared-BPSK carrier line, then checks cyclic PN projections. Surviving windows undergo fractional timing acquisition, per-burst period refinement and disjoint-template symbol projections. It generates the PN sequence algebraically; it does not load a measured chip file or per-meter captured bits to recognise a message.

## From despread BPSK to a checked frame

Coarse carrier removal gets the signal close enough to despread. Residual frequency and phase still rotate the symbol projections. A second-order BPSK Costas loop brings those projections onto the real axis. The first symbol chooses a polarity branch; framing and checksums then determine whether the result is acceptable.

![Real despread symbol projections before residual carrier correction and after the Costas loop, using the same amplitude scale.](img/04-bpsk-constellation.png)

*Figure 4. “Before” already includes coarse carrier removal and despreading. “After” adds residual carrier and phase tracking. These are measured symbol projections, not simulated ideal constellation points.*

Supported bursts contain 104 constant preamble symbols followed by 288, 336 or 384 coded bits. Rate-1/2 decoding produces complete 18-, 21- or 24-byte frames, including sync, checksums and a zero tail byte. Thus the shortest burst has 392 air symbols and 144 decoded bits.

The constraint-length-seven convolutional encoder shifts left, places the newest input at register bit zero, and emits parity through masks `0x6d` and `0x4f`, in that order. Naming the convention matters: reciprocal masks and different descriptions of where sync begins appeared during the research. The maintained [protocol notes](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/PROTOCOL.md) define the implementation's complete-frame convention.

![Real 392-symbol capture through rate-half Viterbi decoding into an 18-byte frame, with header and frame CRC-8 checks passing.](img/05-fec-and-crcs.png)

*Figure 5. We explicitly reran Viterbi on the captured coded bits for this diagram. It required zero corrections. The production decoder first attempts exact inversion and uses Viterbi only when needed. Both paths must pass framing and both CRCs.*

Both CRC-8 checks use polynomial `0x07`, zero initial value, no reflection and zero xorout. In zero-based decoded-bit indices, the header residue over `[8:36]` must be zero. The frame CRC covers `[8:N−16]`, excluding sync, its own checksum and the tail. The receiver also requires sync `C0` and a zero final byte, and rejects more than twelve corrected coded bits. A winning trellis path alone is insufficient. CRCs detect errors; they do not authenticate the transmitter.

![Redacted real 18-byte hex frame annotated with the clear header, masked ID, CRCs, counter fields and flag nibbles, plus a separately labelled arithmetic example.](img/06-clear-frame.png)

*Figure 6. This is the actual frame layout with private nibbles replaced by `X`, including ID bytes shown as `XX` wherever byte-aligned. The three example counter values are illustrative replacements, not measurements. Fields cross byte boundaries, so the annotations use nibble and bit indices.*

The transmitter ID occupies decoded bits 8–27, followed by eight header-CRC bits. For clear frames, three 16-bit counters sit at hex nibbles 18–21, 23–26 and 28–31, newest first. Nibbles 17, 22 and 27 are separate flags of unknown meaning. Including those flags in the arithmetic produces convincing-looking nonsense.

With illustrative counters `120, 110, 104`, we obtain two hourly pulse deltas: `(120 − 110) mod 65536 = 10` and `(110 − 104) mod 65536 = 6`. Three counters preserve two intervals, which can bridge a missed reception when sequence and elapsed time agree. The hourly sequence wraps modulo 256; the counters wrap modulo 65536. Longer gaps and inconsistent sequences require a new baseline rather than invented usage.

A pulse count is not a mechanical dial reading. We need dial observations to establish litres per pulse and the starting offset. Hourly reception also cannot provide instantaneous flow or an immediate leak alarm. Unknown flag and extension fields remain unknown; we do not assign battery, tamper or backflow meanings merely because a datasheet lists those capabilities.

![Actual production receiver CLI scan output from replaying the capture slice, with a masked ID, signal diagnostics and no cumulative counters.](img/08-receiver-log.png)

*Figure 7. Real CLI output from the production decoder on the same bounded slice. We masked the ID and omitted the timestamp. Scan mode used no configured meters, so it emitted no counters and made no MQTT connection or persistent state writes. The screenshot uses a light terminal style for legibility.*

## Where decoding stops: encrypted frames

The 24-byte record below is real. Its outer framing validates, and its clear transmitter ID and RF diagnostics can be recovered. We show its body as opaque blocks. The receiver does not interpret those blocks as water counters.

![Redacted real encrypted 24-byte frame: clear header and masked ID, passing framing checks, RF diagnostics and an opaque body with no usage interpretation.](img/07-encrypted-frame.png)

*Figure 8. Header and outer checks are readable without decrypting the body. `X` blocks withhold ciphertext as well as private header details. RF diagnostics come from reception, not from decrypting a payload field.*

Taggle's [SP3C sheet](https://taggle.com/wp-content/uploads/2025/12/Datasheet-SP3C-002.pdf) and [Cockatoo sheet](https://myriota.lbcdn.io/uploads/Datasheet-Cockatoo-002.pdf) specify AES-128 for Byron telemetry. The [V200HT sheet](https://taggle.com/wp-content/uploads/2023/05/Datasheet-Honeywell-V200HT-V4.pdf) also describes encrypted meter data. These establish manufacturer context; a frame's length and opaque body do not independently prove its exact cipher mode, key handling or model. We retain the archive's encrypted classification without claiming a cryptographic reverse engineering result.

AES-128 has a `2^128` keyspace, approximately `3.4 × 10^38` possible keys. Even an extreme hypothetical rate of `10^18` complete key trials per second would take about `1.1 × 10^13` years to exhaust it, or `5.4 × 10^12` years on average for a uniformly random key. That arithmetic deliberately ignores practical overhead; it is not a feasible hardware proposal.

Knowing likely meter fields does not provide a known-plaintext shortcut to recovering an AES key. A passive receiver observing a one-way transmitter also has no request interface through which to choose messages. We have neither the utility's keys nor evidence of a weakness that changes those facts. Keys are held by the utility and its authorised infrastructure.

These frames belong to other households. **The project does not attempt decryption or key search, and will not accept contributions that do.** We stop at clear framing and RF diagnostics. Production output does not log ciphertext. That makes the boundary concrete in both the implementation and this article.

## Reproducing the figures

All eight figures were rendered with matplotlib from the read-only research archive and decoder code. [The generator](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/blog/make_figures.py) takes explicit capture, analysis and decoder paths. It reads a bounded 1.2-second IQ slice rather than the multi-gigabyte recording, reruns the production CLI, and checks the recovered frame against the archived record. The wideband occupancy panel uses the survey's measured bin summary. The encrypted diagram uses the archived 24-byte record and verifies its framing separately.

The source IQ and full frame archive remain private: they contain other transmitters and household data. Reproduction requires authorised local recordings and matching analysis inputs; the repository supplies the script and redacted figures, not those private inputs. We redact before rendering and retain no raw bit dumps in the publication. Both hexadecimal ID nibbles and cumulative counters are suppressed, including checksum values that could constrain masked fields. The arithmetic example is explicitly separate from captured usage.

## Fork it for your own meter

Start with the [repository](https://github.com/Spicynostalgia/ha-taggle) and the wiki [Quick start / Getting started](https://github.com/Spicynostalgia/ha-taggle/wiki/Getting-Started). The application is MIT licensed. Configure `meter_ids` privately for your own transmitter; set `frequency` to the SDR centre that retains the supported channel, rather than copying a different region's channel plan. The present implementation's supported centre-frequency range and acquisition target still apply.

Set pulse size through `litres_per_count` only after calibration against your own dial, and configure the output target through `mqtt` for your broker and Home Assistant discovery, or your own MQTT consumer. Changing the output consumer does not extend RF compatibility. Keep the supported 2.4 MS/s rate, allow an hourly transmission opportunity, and check ownership against your own meter before using a reading.

Receive only your own meter. Keep identifiers, recordings and logs private, and redact photos before sharing a compatibility result. A Taggle label or council rollout is a reason to investigate, not a guarantee of a clear compatible signal. For the transmitter we verified, however, a cheap SDR and a carefully checked decoding chain were enough to bring hourly pulses into a local dashboard.
