# Draft pitch for the maintainer to send

Subject: Decoding Taggle water meters at 922 MHz with an RTL-SDR

Hi rtl-sdr.com team,

We used an RTL-SDR Blog V4 to read our own Taggle water meter in Gladstone, QLD. Our write-up shows how we turned its hourly pulse counts into local MQTT and Home Assistant readings.

We follow a real recording from a noise-like burst near 922 MHz to a checked frame. We recover the signal with a 4095-chip pattern seen through a 2.4 MHz passband, track the BPSK carrier, decode the rate-1/2 convolutional code and check two independent CRC-8s. Reproducible matplotlib figures and an actual receiver replay show each step.

We also show real 24-byte encrypted frames. We can check framing and RF diagnostics, but we do not decrypt usage or search for keys. The clear example is the author’s own meter, 527814 / 0x80DC6, with hex and counters shown with his permission for this post only. Neighbours’ IDs and the encrypted example stay masked. We have field-verified one transmitter; yours may differ.

Would this suit a reader project feature? The MIT source, full article and setup guide are linked below.

## Image picks

- [Band survey and confirmed-burst spectrum](img/01-band-occupancy.png): where we looked for the signal.
- [PN correlation](img/03-pn-correlation.png): where the real recording matches the 4095-chip pattern.
- [Before/after BPSK constellation](img/04-bpsk-constellation.png): how carrier tracking aligns the measured symbols.
- [Encrypted-frame boundary](img/07-encrypted-frame.png): the header we can read and the body we cannot.

## Links to include

- Article: https://ha-taggle.dancloud.au/blog/decoding-taggle/
- Repository article: https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/blog/decoding-taggle-922mhz.md
- Source: https://github.com/Spicynostalgia/ha-taggle
- Wiki article: https://github.com/Spicynostalgia/ha-taggle/wiki/Blog-Decoding-Taggle
- Quick start: https://github.com/Spicynostalgia/ha-taggle/wiki/Getting-Started

These article URLs are intended destinations. This task commits locally only; confirm that the article is published before sending. No email has been sent.
