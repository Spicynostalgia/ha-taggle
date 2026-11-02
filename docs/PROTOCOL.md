# Supported radio format

This is a description of the supported receive path, not a complete specification of every transmitter. Unknown flags and opaque fields are left uninterpreted. CRC validation detects errors, not authenticity.

## Physical and channel coding

- Nominal centre frequency: 922200000 Hz; sample rate: 2400000 samples/s, unsigned 8-bit interleaved I/Q.
- Target carrier near 921995000 Hz; default acquisition searches ±100 kHz around its expected baseband offset. The configured centre must retain this band. This does not scan every channel in 915–928 MHz.
- BPSK, approximately 1172.66 coded symbols/s. The fitted period is near 2046.625 ADC samples and is refined for each burst.
- 4095 PN chips per coded symbol, approximately 4.802 Mchip/s on the nominal ADC clock. Absolute clock accuracy is not established.
- Forward polynomial `x^12+x^9+x^6+x^5+x^2+x+1`, packed as `0x1267`. Forward recurrence:

```text
s[n+12] = s[n+9] XOR s[n+6] XOR s[n+5]
          XOR s[n+2] XOR s[n+1] XOR s[n]
```

The generator starts with state 1, takes its least significant bit, shifts right, and inserts the parity of state masked by `0x267` into bit 11. Binary 1 maps to −1; cyclic phase and overall RF polarity are arbitrary. No recovered chip file is needed.

Each frame has 104 constant symbols (zero under the chosen polarity), then 288, 336 or 384 coded bits. Total lengths are 392, 440 or 488 symbols. Convolutional encoding starts at state zero and, for each input bit, uses:

```text
reg = (state << 1) | input_bit
emit parity(reg & 0x6d), parity(reg & 0x4f)
state = reg & 0x3f
```

The newest input is register bit 0. These masks are octal 155 and 117 in this convention. The final zero byte flushes the state. The decoder first tries exact inversion, then a hard-decision Viterbi decode with zero initial and terminal states. More than 12 corrected coded bits is rejected. Sync, tail and both CRC checks are mandatory after either decoder.

Acquisition first screens the squared BPSK carrier, then checks cyclic projections against the known PN template. Fractional timing, disjoint template training, a Costas loop and per-burst clock refinement recover symbols from the surviving RF band. No per-meter priors, measured waveform files or captured bits are loaded.

## Decoded layout

Bit indices are zero-based, MSB-first, after channel decoding. Hex nibble indices are also zero-based. All supported formats contain:

| Bits | Meaning |
| --- | --- |
| 0–7 | `0xc0` sync/header marker |
| 8–27 | 20-bit transmitter ID |
| 28–35 | ID header CRC, making the residue over bits 8–35 zero |
| 36 through N−17 | Format-dependent body |
| N−16 through N−9 | Full-frame CRC-8 |
| N−8 through N−1 | Zero tail byte |

Both CRCs use polynomial `0x07`, initial zero, xorout zero, no reflection. The frame CRC covers bits 8 through N−17 inclusive, excluding sync, checksum and tail. This matches the CRC-8/SMBUS parameter set; it does not identify the protocol as SMBus. The standard ASCII `123456789` check value is `0xf4`.

In the **18/21-byte clear formats**:

| Hex nibbles | Interpretation |
| --- | --- |
| 9 | Format nibble, retained uninterpreted |
| 10 | Unknown |
| 11–12 | 8-bit hourly sequence |
| 13–16 | Unknown |
| 17, 22, 27 | Separate 4-bit flags, meaning unknown |
| 18–21, 23–26, 28–31 | Three 16-bit raw counters, newest first |
| 32 onward, before CRC/tail | Additional unknown bytes in the 21-byte format |

Never include the flag nibbles in counter arithmetic. Adjacent counter differences are modulo 65536. Three counters recover two hourly deltas. The sequence is modulo 256; elapsed UTC time disambiguates long sequence wraps. An inconsistent backwards sequence establishes a new baseline rather than estimating missing usage. The daily observed sum uses the local date of each estimated interval **end**. It is not a midnight-to-midnight billing register difference.

The **24-byte format** has an opaque encrypted body. The receiver validates framing and extracts only the clear ID and RF diagnostics. It does not interpret that body as counters, log ciphertext, or implement any decryption or key-search path.

## Scan output

Scan mode emits one JSON object per decoded frame. `time` is the frame's sample-derived timestamp in ISO-8601 UTC, including when replaying a recording with `--start-utc`; it is not the time decoding finishes. `snr_median_db` and `signal_level_dbfs` are rounded to one decimal place. Fictional unconfigured-meter example:

```json
{"time": "2026-01-01T12:15:00+00:00", "meter_id": 123456, "snr_median_db": 30.1, "signal_level_dbfs": -40.9}
```

A configured clear meter also includes `"counts": [120, 110, 104]` (newest first). Unconfigured IDs and encrypted frames never expose counts in scan output. Scan mode prints heard IDs, so keep its output private; it writes no state or JSONL logs and makes no MQTT connection. Normal reception logs configured IDs only, with counts-only heartbeats for other meters every 15 minutes.

## Generated test signals

`tests/synthetic.py` constructs nibble-aligned fake headers and counters, solves the header CRC, appends the frame CRC/tail, convolutionally encodes, and spreads the result using `0x1267`. IQ is synthesized at four times ADC rate and low-pass filtered **before** decimation, with fractional timing, carrier offset, slow phase drift and seeded noise. This exercises partial-band acquisition without manufacturing aliases. It is an offline test generator only.

## Integration references

The MQTT integration follows the [Home Assistant MQTT sensor schema](https://www.home-assistant.io/integrations/sensor.mqtt/), including water units, state classes and discovery availability. Add-on packaging follows the [Home Assistant app configuration reference](https://developers.home-assistant.io/docs/apps/configuration/). Card distribution follows [HACS dashboard plugin packaging](https://hacs.dev/docs/publish/plugin/).
