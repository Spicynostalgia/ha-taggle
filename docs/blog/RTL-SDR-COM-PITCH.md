# Draft pitch to rtl-sdr.com

Subject: Decoding Taggle water meters at 922 MHz with an RTL-SDR

Hi rtl-sdr.com team,

I decoded my Taggle water meter in Gladstone, QLD, with an RTL-SDR Blog V4 and Python, then sent hourly readings to MQTT and Home Assistant. The unusual part is the DSSS/BPSK signal: each symbol carries a 4095-chip spreading pattern.

The write-up follows one real frame from IQ to litres: removing a −208 kHz carrier offset, despreading, tracking BPSK, undoing the rate-1/2 convolutional code and checking both CRC-8s. It shows the coded pairs, all 18 decoded bytes, and counter differences worth 55 L and 25 L on my calibrated V100. Fifteen unblurred figures include inspectrum waterfalls, Universal Radio Hacker (URH) views of despread symbols, measured matplotlib plots and calibration checks.

A 24-byte encrypted example shows its clear ID and ciphertext in full, but no usage. The project does not attempt decryption or key search. Only one transmitter is field-verified; other installations remain unverified. I built it with [AI coding assistants](https://github.com/Spicynostalgia/ha-taggle/wiki/AI-Disclosure). The article, MIT source and setup links are below if this suits a reader project feature.

Thanks,
Dan

## Image picks

- [Clear burst in inspectrum](img/waterfall-clear-burst06.png): full receiver passband, MHz and time axes from real IQ.
- [Clear frame in Universal Radio Hacker](img/urh-clear-burst06.png): decoder’s despread stream at 20 samples per symbol, all bits unblurred.
- [Clear-frame layout](img/06-clear-frame.png): my ID, complete hex and measured counters.
- [Encrypted-frame layout](img/07-encrypted-frame.png): burst 08’s clear ID and ciphertext, fully visible; usage stays unreadable.

## Links

- Article: https://ha-taggle.dancloud.au/blog/decoding-taggle/
- GitHub edition: https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/blog/decoding-taggle-922mhz.md
- Wiki edition: https://github.com/Spicynostalgia/ha-taggle/wiki/Blog-Decoding-Taggle
- MIT source: https://github.com/Spicynostalgia/ha-taggle
- Quick start: https://github.com/Spicynostalgia/ha-taggle/wiki/Getting-Started

Draft only; I have not sent this pitch, pushed this revision or deployed it.
