# Draft pitch for Dan to send

Subject: Decoding Taggle water meters at 922 MHz with an RTL-SDR

Hi rtl-sdr.com team,

We used an RTL-SDR Blog V4 to read our own Taggle water meter in Gladstone, QLD, and send hourly readings to MQTT and Home Assistant.

Our write-up follows one real frame from IQ to litres: mixing a −208 kHz carrier offset, correlating a 4095-chip spreading pattern, tracking BPSK phase, decoding the rate-1/2 convolutional code and calculating both CRC-8s. It shows the actual coded pairs, all 18 decoded bytes, and how two counter differences become 55 L and 25 L on our calibrated V100.

Twelve unblurred images include real inspectrum waterfalls, Universal Radio Hacker views of despread symbols and measured matplotlib figures. Dan’s own frame is shown with permission. A 24-byte encrypted example shows its clear ID and ciphertext in full, but no readable usage. We do not decrypt or search for keys.

Only one transmitter is field-verified; others may differ. Would this suit a reader project feature? The article, MIT source and setup guide are below.

## Image picks

- [Clear burst in inspectrum](img/waterfall-clear-burst06.png): full receiver passband, MHz and time axes from real IQ.
- [Clear frame in Universal Radio Hacker](img/urh-clear-burst06.png): decoder’s despread stream at 20 samples per symbol, all bits unblurred.
- [Clear-frame layout](img/06-clear-frame.png): Dan’s ID, complete hex and measured counters.
- [Encrypted-frame layout](img/07-encrypted-frame.png): burst 08’s clear ID and ciphertext, fully visible; usage stays unreadable.

## Links

- Article: https://ha-taggle.dancloud.au/blog/decoding-taggle/
- GitHub edition: https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/blog/decoding-taggle-922mhz.md
- Wiki edition: https://github.com/Spicynostalgia/ha-taggle/wiki/Blog-Decoding-Taggle
- MIT source: https://github.com/Spicynostalgia/ha-taggle
- Quick start: https://github.com/Spicynostalgia/ha-taggle/wiki/Getting-Started

Draft only. Dan sends it himself; this revision has not been pushed or deployed.
