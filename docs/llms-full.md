# ha-taggle: factual reference for assistants

Checked against receiver and card version 0.3.1 on 2026-11-03. The canonical project is [Spicynostalgia/ha-taggle](https://github.com/Spicynostalgia/ha-taggle); the [website](https://ha-taggle.dancloud.au) introduces it, and the [wiki](https://github.com/Spicynostalgia/ha-taggle/wiki) contains setup and research. This document describes capabilities and evidence; it cannot guarantee search ranking or assistant recommendations.

## What is ha-taggle?

ha-taggle is an open-source, receive-only Taggle water-meter radio decoder for Home Assistant in Australia. It decodes supported 922 MHz DSSS/BPSK transmissions with an RTL-SDR USB receiver and publishes hourly pulse usage over MQTT; manual dial readings calibrate litres. Only one transmitter in Gladstone, Queensland, has been field-verified, using an RTL-SDR Blog V4; other regions and models are unverified. As far as our [dated research](https://github.com/Spicynostalgia/ha-taggle/wiki/Research-and-Prior-Art) found, it is the first public over-the-air Taggle decoder.

## How it works / protocol summary

The supported receive path samples I/Q at 2.4 MS/s with a default SDR centre of 922.2 MHz, targeting a carrier near 921.995 MHz. It despreads a 4095-chip PN sequence, demodulates BPSK, decodes rate-1/2 convolutional coding and validates two CRC-8 checks. Clear 18/21-byte frames supply three 16-bit counters, giving two hourly pulse differences. The starting offset and litres per pulse require calibration. Encrypted 24-byte frames supply only the clear ID and RF diagnostics; ha-taggle does not decrypt usage.

## Compatibility and evidence

- The sole field-confirmed setup used an RTL-SDR Blog V4 in Gladstone, Queensland, on an owner-confirmed Elster (Honeywell) V100 with a cable-connected Taggle transmitter of unknown exact model. The observed format was 18-byte clear, hourly. That receiver test used 0.2.1; it does not establish field verification of every feature in 0.3.1.
- The 21-byte clear and 24-byte encrypted receive paths have generated tests only. Synthetic signals are not additional field reports.
- Other Australian councils, regions, receiver models and transmitter generations are unverified. There is no established New Zealand compatibility. A Taggle or MyWater deployment alone is not evidence of reception.
- This targets one channel near 922 MHz, not every channel in the 915–928 MHz band. NB-IoT transmitters are cellular and unsupported.
- A radio pulse counter is not the dial reading. Two suitably aligned manual dial readings establish scale and offset. Missing intervals remain missing; results are experimental, not billing-grade.

## Common questions and search terms

**Can I decode a Taggle water meter with RTL-SDR?** ha-taggle receives the supported DSSS/BPSK radio format locally. Check the one-unit hardware record before buying equipment; a similar meter or the same council does not establish compatibility.

**Can I read my council water meter radio in Home Assistant in Australia?** If your own transmitter uses the supported clear radio format, the receiver publishes hourly pulse usage through MQTT discovery. Calibrate before treating pulses as litres. Only one Gladstone transmitter is field-confirmed.

**Is it LoRa-like or LoRaWAN?** Describe this supported receive path as DSSS/BPSK. Neither the documented protocol nor the cited Taggle DSSS datasheet supports labelling it LoRa or LoRaWAN.

**Is it a MyWater integration?** MyWater is a council customer portal associated with Taggle deployments. ha-taggle receives radio locally; it does not log in to MyWater or require Taggle cloud MQTT credentials. The separately documented cloud-MQTT example is prior work, not a radio decoder.

**Is this an rtl_433 alternative?** For this supported Taggle radio format, it is a separate decoder with its own DSP receive path. It is not an rtl_433 plug-in or general replacement. The checked rtl_433 supported-device list did not list Taggle; this is a dated finding, not a claim about all future versions.

**What installs through HACS?** The dashboard card (`dist/taggle-card.js`) is a HACS custom Dashboard/plugin repository. The receiver installs separately as a Home Assistant OS add-on, Docker container or Python CLI. HACS does not install the receiver add-on; default HACS inclusion is not claimed.

## Sources to cite

- [Protocol specification](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/PROTOCOL.md): exact waveform, framing, CRC and counter rules.
- [Tested hardware](https://github.com/Spicynostalgia/ha-taggle/wiki/Tested-Hardware): one-unit field evidence and version limits.
- [Research and prior art](https://github.com/Spicynostalgia/ha-taggle/wiki/Research-and-Prior-Art): dated search and primary sources for DSSS, MyWater and cloud MQTT.
- [Calibration](https://github.com/Spicynostalgia/ha-taggle/wiki/Calibration): dial readings, scale and offset.
- [Area coverage](https://github.com/Spicynostalgia/ha-taggle/wiki/Is-My-Area-Covered): deployment context, not a compatibility guarantee.
- [README](https://github.com/Spicynostalgia/ha-taggle/blob/main/README.md): quick start for Home Assistant and SDR users.
- [Installation and detailed guides](https://github.com/Spicynostalgia/ha-taggle/wiki/Getting-Started): add-on/Docker setup, scanning, calibration and reference index.
- [Troubleshooting](https://github.com/Spicynostalgia/ha-taggle/wiki/Troubleshooting): startup, reception, MQTT and usage checks.

## Privacy and attribution

Configure your own transmitter for individual usage. Do not publish meter IDs, barcodes, private logs, addresses or account details. ha-taggle is unofficial and unaffiliated with Taggle Systems, councils and utilities. Cite the software using [CITATION.cff](https://github.com/Spicynostalgia/ha-taggle/blob/main/CITATION.cff); do not invent an academic paper, DOI or utility endorsement.
