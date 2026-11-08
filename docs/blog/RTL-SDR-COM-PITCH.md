# Draft pitch for the maintainer to send

Subject: Decoding Taggle water meters at 922 MHz with an RTL-SDR

Hi rtl-sdr.com team,

We've written up how we used an RTL-SDR Blog V4 to receive our own Taggle water-meter transmitter in Gladstone, QLD, and turn its hourly pulse counts into local MQTT and Home Assistant readings.

The interesting part is the receive chain: a noise-like DSSS burst near 922 MHz, a recovered 4095-chip PN sequence observed through a 2.4 MHz passband, BPSK carrier tracking, rate-1/2 convolutional decoding and two independent CRC-8 checks. The article follows real IQ through each stage, with reproducible matplotlib figures and an actual receiver replay.

It also shows where we stop: real 24-byte encrypted frames expose framing and RF diagnostics, but we do not decrypt usage or search for keys. Every ID and cumulative counter is masked. Only one transmitter is field-verified; this isn't a universal Taggle compatibility claim.

Would this suit a reader project feature? The MIT source, full article and setup guide are linked below.

## Image picks

- [Band survey and confirmed-burst spectrum](img/01-band-occupancy.png): the RF starting point and its limits.
- [PN correlation](img/03-pn-correlation.png): the 4095-chip match from real IQ.
- [Before/after BPSK constellation](img/04-bpsk-constellation.png): measured symbol recovery.
- [Encrypted-frame boundary](img/07-encrypted-frame.png): readable header, opaque usage body.

## Links to include

- Article: https://ha-taggle.dancloud.au/blog/decoding-taggle/
- Repository article: https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/blog/decoding-taggle-922mhz.md
- Source: https://github.com/Spicynostalgia/ha-taggle
- Wiki article: https://github.com/Spicynostalgia/ha-taggle/wiki/Blog-Decoding-Taggle
- Quick start: https://github.com/Spicynostalgia/ha-taggle/wiki/Getting-Started

These article URLs are intended destinations. This task commits locally only; confirm that the article is published before sending. No email has been sent.
