# Discoverability handoff

Prepared **2026-11-03** for receiver and card **0.3.1**. Everything below is a draft for the maintainer. No GitHub settings, submissions, forum posts or Reddit posts have been changed or sent. Search visibility and assistant recommendations cannot be guaranteed.

## GitHub About settings

Set the website to **https://ha-taggle.dancloud.au** and use this exact repository description (under GitHub's 350-character limit):

```text
Decode supported Taggle water meters near 922 MHz with RTL-SDR and Home Assistant MQTT. Receive-only, local, open source; hourly pulse usage with guided litre calibration. HA add-on, Docker, Python CLI and HACS card. Field-tested on one transmitter in Gladstone, Australia; other setups unverified.
```

Use these **14 topics**, in this order:

```text
home-assistant, taggle, water-meter, rtl-sdr, sdr, hacs, home-assistant-addon, smart-meter, australia, mqtt, iot, energy-monitoring, software-defined-radio, lovelace-custom-card
```

The broad terms help discovery; `taggle` is the exact vendor term, not a claim of a popular existing topic. `energy-monitoring` describes Home Assistant's water/usage dashboard context, not electricity decoding. Do not add `lora`, `lorawan`, `nb-iot` or `rtl-433`: they could imply unsupported protocol or plug-in support.

Topic usage checked on GitHub's topic pages on 2026-11-03 (counts are snapshots, not search-volume estimates):

| Topic | Public repositories shown | Source |
| --- | ---: | --- |
| home-assistant | 29,026 | [GitHub topic](https://github.com/topics/home-assistant) |
| rtl-sdr | 742 | [GitHub topic](https://github.com/topics/rtl-sdr) |
| sdr | 1,931 | [GitHub topic](https://github.com/topics/sdr) |
| hacs | 17,458 | [GitHub topic](https://github.com/topics/hacs) |
| home-assistant-addon | 620 | [GitHub topic](https://github.com/topics/home-assistant-addon) |
| water-meter | 111 | [GitHub topic](https://github.com/topics/water-meter) |
| smart-meter | 383 | [GitHub topic](https://github.com/topics/smart-meter) |
| australia | 1,238 | [GitHub topic](https://github.com/topics/australia) |
| mqtt | 14,616 | [GitHub topic](https://github.com/topics/mqtt) |
| iot | 36,062 | [GitHub topic](https://github.com/topics/iot) |
| energy-monitoring | 692 | [GitHub topic](https://github.com/topics/energy-monitoring) |

`software-defined-radio` is also an [established GitHub topic](https://github.com/topics/software-defined-radio). `lovelace-custom-card` accurately describes the dashboard component. Prefer the singular `home-assistant-addon` above to a collection-oriented topic; it had substantially more listed repositories than the `homeassistant-addon` spelling when checked.

## Social preview suggestion

Use the existing [brand social preview PNG](images/brand/social-preview.png) and its [SVG source](images/brand/social-preview.svg). The existing PNG is 2560 × 1280; export a 1280 × 640 copy for upload, keeping the project identity consistent with the README. Suggested next revision: headline **“Decode your Taggle water meter”**, subline **“RTL-SDR → MQTT → Home Assistant”**, and a readable qualifier **“Experimental · one Gladstone transmitter verified”**. Use the logo and a synthetic card crop; include no real ID, barcode, dial photo, owner name, email or address. Uploading or replacing the GitHub social image is a separate maintainer action.

## Submission drafts — not posted

Recheck each destination's rules and duplicate suggestions immediately before submission. Disclose maintainer affiliation and AI assistance where appropriate; the repository already has an [AI disclosure](https://github.com/Spicynostalgia/ha-taggle/wiki/AI-Disclosure). Use the [research note](https://github.com/Spicynostalgia/ha-taggle/wiki/Research-and-Prior-Art) for qualified priority claims, not an unqualified “world first”.

### awesome-home-assistant

Target: [frenck/awesome-home-assistant](https://github.com/frenck/awesome-home-assistant), **Apps → Third Party Apps**. This project is a receiver add-on plus card, not a `custom_components` integration. The [current contribution rules](https://github.com/frenck/awesome-home-assistant/blob/main/.github/CONTRIBUTING.md) require software repositories to be at least six months old, recently active, unarchived and OSI-licensed. **Hold this draft until the six-month age requirement is met**; the GitHub API reports creation on 2026-11-02, so the earliest age-eligible date is **2027-05-02** (recheck all rules then). The list also asks for community recommendation rather than promotion; explain the narrow use case and affiliation. Add one link at the end of the appropriate category after checking for duplicates.

Draft PR title: **Add ha-taggle water-meter receiver**

Draft entry:

```markdown
- [ha-taggle](https://github.com/Spicynostalgia/ha-taggle) - Receive-only Taggle water-meter decoder using RTL-SDR and MQTT, with a companion dashboard card.
```

Draft PR body:

> I maintain ha-taggle, an MIT-licensed local receiver for the supported Taggle water-meter radio format. It provides a Home Assistant OS add-on and MQTT discovery, with Docker/CLI routes and a companion HACS card. The unusual part is its documented DSSS/BPSK decoder near 922 MHz. Field evidence is limited to one transmitter in Gladstone, Australia; other setups are unverified. Manual calibration supplies litres. The README includes installation, screenshots, protocol details and explicit compatibility limits. This entry is intended for Third Party Apps; it is not a core or custom-component integration.

### awesome-sdr / awesome-rtl-sdr

Preferred target: [vkvbit/awesome-sdr](https://github.com/vkvbit/awesome-sdr), **Awesome SDR Projects**, alongside other specialised decoders. Read its [contribution rules](https://github.com/vkvbit/awesome-sdr/blob/main/CONTRIBUTING.md) again before opening a PR.

Alternative: [Schm1tz1/awesome-rtl-sdr](https://github.com/Schm1tz1/awesome-rtl-sdr), **Command-Line Tools**. This is a software meta-package with installers, rather than purely a curated list; confirm that a link-only addition fits before proposing installer changes. Do not submit duplicate requests to multiple lists without considering fit.

Draft PR title: **Add ha-taggle Taggle DSSS water-meter decoder**

Draft entry:

```markdown
- [ha-taggle](https://github.com/Spicynostalgia/ha-taggle) - Receive-only RTL-SDR decoder for supported Taggle DSSS/BPSK water-meter transmissions near 922 MHz, with MQTT output and documented protocol limits.
```

Draft PR body:

> I maintain ha-taggle and propose it as a specialised SDR decoder. It implements PN despreading, BPSK demodulation, convolutional decoding and two CRC checks, with a published protocol specification and generated IQ tests. It extracts pulse counters from supported clear frames; encrypted bodies are not decrypted. One Gladstone transmitter has field confirmation with an RTL-SDR Blog V4. The project is MIT-licensed and includes a Python CLI as well as Home Assistant packaging. Other transmitter models, areas and SDRs are unverified.

### rtl_433 pointer discussion

Target: [rtl_433 Discussions](https://github.com/merbanan/rtl_433/discussions), using a suitable general/project category if available. The [device-contribution guide](https://github.com/merbanan/rtl_433/blob/master/docs/CONTRIBUTING.md) requires signals and supporting details before device-support issues. **This draft asks about a related-project pointer, not a device-support issue.** It supplies no private captures and does not ask maintainers to implement a decoder. If Discussions is unavailable, ask about the appropriate documentation route rather than opening a support issue that lacks required samples.

Draft title: **Related-project pointer: Taggle water-meter DSSS/BPSK receiver**

Draft body:

> I maintain [ha-taggle](https://github.com/Spicynostalgia/ha-taggle), a receive-only RTL-SDR decoder for the supported Taggle water-meter radio format near 922 MHz. People looking for Australian Taggle support may arrive here through rtl_433 searches, so I wondered whether a related-project pointer would be useful, and where it would fit.
>
> It uses its own DSSS/BPSK receive path; it is not an rtl_433 decoder or plug-in. The [protocol specification](https://github.com/Spicynostalgia/ha-taggle/blob/main/docs/PROTOCOL.md) documents PN spreading, convolutional coding, CRCs and counter layout. The checked supported-device list had no Taggle entry; please correct me if I missed existing work.
>
> Only one transmitter in Gladstone has field confirmation, using an RTL-SDR Blog V4. Clear 18/21-byte handling yields pulse counters; only 18-byte clear has field evidence. Encrypted 24-byte handling exposes ID and diagnostics only, with generated tests. I am proposing a documentation pointer, not requesting device support or uploading private radio captures.

### HACS default repository checklist

**Scope: dashboard card, category `plugin` (shown as Dashboard), not the receiver add-on. Default inclusion has not been requested or established.** Sources: [general requirements](https://hacs.dev/docs/publish/start/), [dashboard packaging](https://hacs.dev/docs/publish/plugin/), [default inclusion](https://hacs.dev/docs/publish/include/).

- [x] Local `hacs.json` supplies `name`, `filename: taggle-card.js` and `render_readme: true`; `dist/taggle-card.js` exists.
- [x] README has installation steps and images; MIT licence is present.
- [x] CI defines `hacs/action` with `category: plugin` and comments disabled.
- [ ] Confirm the **published** repository is public, unarchived, has issues enabled, and has appropriate About description/topics.
- [ ] Confirm HACS validation passes on the published revision, including the explicit filename override (`ha-taggle` and `taggle-card.js` differ). Local packaging alone is not approval.
- [ ] Check README images render in HACS. If using releases, verify a published release and downloadable card asset; a tag alone is insufficient.
- [ ] Owner or major contributor submits: fork [hacs/default](https://github.com/hacs/default), create a feature branch from `master`, add `Spicynostalgia/ha-taggle` to the sorted `plugin` JSON list, preserve exact case, and allow maintainer edits.
- [ ] Pass all applicable default-list CI checks, then await review and the scheduled scan after merging. `hassfest`/brands checks apply to integrations, not this dashboard card.

Draft PR title: **Add Spicynostalgia/ha-taggle dashboard card**

Draft PR body:

> I maintain this dashboard card and request default HACS inclusion in the plugin category. It displays ha-taggle water usage and calibration through Home Assistant MQTT entities. The receiver is installed separately as an add-on, Docker container or Python CLI. The repository includes `hacs.json`, `dist/taggle-card.js`, screenshots, installation instructions and an MIT licence. Compatibility is experimental and limited to one field-confirmed transmitter. Before submitting, I will attach the passing HACS validation run and confirm the published card is installable through HACS.

### Home Assistant community — Share your Projects

Target: [Share your Projects](https://community.home-assistant.io/c/projects/9). Recheck category and forum guidelines before posting; attach only a synthetic screenshot such as [card-light.png](images/card-light.png).

Draft title: **ha-taggle: receive your Taggle water meter locally with RTL-SDR and MQTT (Australia)**

Draft post:

> I maintain [ha-taggle](https://github.com/Spicynostalgia/ha-taggle), an experimental, open-source way to receive supported Taggle water-meter transmissions locally and show hourly water use in Home Assistant. An RTL-SDR listens near 922 MHz and the receiver publishes through MQTT discovery. There is a Home Assistant OS add-on, Docker/CLI setup and a companion HACS dashboard card.
>
> So far, exactly one transmitter in Gladstone, Queensland, has been verified, with an RTL-SDR Blog V4 on an owner-confirmed Elster V100. Other models and councils are unverified, so please check the [hardware record](https://github.com/Spicynostalgia/ha-taggle/wiki/Tested-Hardware) before buying anything.
>
> The supported radio format is DSSS/BPSK. Clear messages carry pulse counters, not the dial reading; guided calibration uses manual dial readings to work out litres and offset. Encrypted messages provide ID and signal diagnostics only, and NB-IoT transmitters are unsupported. It is receive-only, runs locally and needs no MyWater login or cloud MQTT account. It is not affiliated with Taggle or a council, and is not billing-grade.
>
> The [README](https://github.com/Spicynostalgia/ha-taggle#readme) has the setup steps; the [wiki](https://github.com/Spicynostalgia/ha-taggle/wiki) covers calibration and the protocol. The project documents its AI-assisted development and verification limits. If you already have suitable hardware, compatibility reports would help: council/region, meter/transmitter model if known, receiver model, software version and whether calibrated usage worked. Please keep IDs, barcodes, private logs and addresses out of public replies. Leave the utility's meter and transmitter in place.

### r/homeassistant

Target: [r/homeassistant](https://www.reddit.com/r/homeassistant/). Check current rules and any designated project/self-promotion thread before posting; this is a draft, not a scheduling instruction.

Draft title: **I made a local Taggle water-meter receiver for Home Assistant using RTL-SDR — one Gladstone unit tested**

Draft post:

> I maintain **ha-taggle**, an experimental MIT-licensed receiver for supported Australian Taggle water-meter radio messages. RTL-SDR → local decoder → MQTT discovery → Home Assistant. It has an HA OS add-on, Docker/CLI routes and a HACS dashboard card.
>
> The big limit: **only one transmitter in Gladstone, QLD, is field-confirmed**, using an RTL-SDR Blog V4. Other meters and areas are unverified. It decodes the supported DSSS/BPSK format near 922 MHz; clear messages give pulse counts, and manual dial readings calibrate litres. Encrypted bodies are not decrypted, and NB-IoT units are unsupported. No MyWater login is needed. It only listens and is not affiliated with Taggle or a council.
>
> [Source, screenshots and installation](https://github.com/Spicynostalgia/ha-taggle) · [Tested hardware](https://github.com/Spicynostalgia/ha-taggle/wiki/Tested-Hardware) · [AI-assisted development disclosure](https://github.com/Spicynostalgia/ha-taggle/wiki/AI-Disclosure)
>
> If you already own suitable hardware, reports of working or non-working models would be useful. Please share model, broad council/region, receiver and software version only; keep real IDs, barcodes, private logs, names and addresses private. Check compatibility before spending money. This is experimental, not billing-grade monitoring.

## Keeping facts aligned

When capabilities change, update the README entity statement, `llms.txt`, `docs/llms-full.md`, `CITATION.cff`, `docs/PROTOCOL.md` summary, and wiki Home/Protocol/How-It-Works together. Re-run the prior-art search before repeating the first-public claim. Do not imply HACS default acceptance, council-wide support, cloud-service integration or decryption. `llms.txt` at the repository root is a reading guide; it is not automatically served at the website's `/llms.txt`. Website deployment is outside this handoff.
