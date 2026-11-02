---
name: Taggle water meter card
description: Theme-aware household water use, observed history and dial calibration.
colors:
  water: "var(--primary-color,#2bb3d6)"
  ink: "var(--primary-text-color,#0d2233)"
  muted: "var(--secondary-text-color,#5a6f7e)"
  surface: "var(--ha-card-background,var(--card-background-color,#fff))"
  line: "var(--divider-color,#e3eaee)"
  card-border: "var(--ha-card-border-color,var(--divider-color,#e3eaee))"
  chip: "color-mix(in srgb,var(--primary-color,#2bb3d6) 12%,var(--ha-card-background,var(--card-background-color,#fff)))"
  chip-ink: "color-mix(in srgb,var(--primary-color,#2bb3d6) 38%,var(--primary-text-color,#0d2233))"
  success: "var(--success-color,#1d8a4a)"
  warning: "var(--warning-color,#e07b1f)"
  error: "var(--error-color,#b3261e)"
  control-ink: "var(--primary-text-color,#171717)"
typography:
  display: {fontFamily: "var(--primary-font-family,Manrope,system-ui,sans-serif)", fontSize: "52px", fontWeight: 800, lineHeight: 1.05, letterSpacing: "-.03em"}
  title: {fontFamily: "var(--primary-font-family,Manrope,system-ui,sans-serif)", fontSize: "16px", fontWeight: 700, lineHeight: 1.4}
  body: {fontFamily: "var(--primary-font-family,Manrope,system-ui,sans-serif)", fontSize: "14px", lineHeight: 1.5}
  metric: {fontFamily: "var(--primary-font-family,Manrope,system-ui,sans-serif)", fontSize: "22px", fontWeight: 800}
  label: {fontFamily: "var(--primary-font-family,Manrope,system-ui,sans-serif)", fontSize: "12px"}
rounded:
  card: "var(--ha-card-border-radius,24px)"
  status: "14px"
  read-now: "10px"
  control: "6px"
  hourly-bar: "4px"
  daily-bar: "3px"
  chip: "999px"
spacing:
  compact: "8px"
  control-gap: "12px"
  mobile-gutter: "16px"
  section: "20px"
  gutter: "24px"
components:
  card: {backgroundColor: "{colors.surface}", textColor: "{colors.ink}", rounded: "{rounded.card}"}
  calibration-chip: {backgroundColor: "{colors.chip}", textColor: "{colors.chip-ink}", rounded: "{rounded.chip}", padding: "5px 10px"}
  save-reading: {textColor: "{colors.control-ink}", rounded: "{rounded.control}", padding: "10px 20px"}
  reading-input: {backgroundColor: "{colors.surface}", textColor: "{colors.control-ink}", rounded: "{rounded.control}", padding: "10px 8px"}
  unit-selector: {backgroundColor: "{colors.surface}", textColor: "{colors.ink}", rounded: "{rounded.control}", width: "100%"}
  usage-hero: {typography: "{typography.display}"}
  hourly-history: {height: "140px"}
  status-row: {backgroundColor: "{colors.chip}", rounded: "{rounded.status}", padding: "12px 14px"}
  calibration-disclosure: {textColor: "{colors.chip-ink}"}
---

# Design System: Taggle water meter card

## Overview

**Creative North Star: "Water use at a glance"**

This documents the user-approved dashboard card, not the repository's wider brand or README artwork. The wave, usual-day ring and dominant Today value frame a compact, calm reading of household water use. Observed data and reception gaps stay explicit; dial calibration remains available within the same card.

**Key Characteristics:**
- Theme-led water accent and quiet surface divisions.
- Large numeric hierarchy with compact supporting context.
- Visible observation gaps, progressive disclosure and practical dial controls.

## Colors

Primary water colors the wave, live dot, ring, peak bars and yesterday. Neutral ink, muted text, surface and line follow Home Assistant. Success and warning distinguish leak states; warning also marks ring overflow. Error marks calibration and form failures. Chips and chart fills mix the accent with the current surface; the sidecar records the remaining state recipes.

**The Theme Authority Rule.** The frontmatter's CSS expressions are normative. Home Assistant variables override every fallback; screenshot fixture hex values illustrate themes and do not define a separate palette.

## Typography

Use the inherited Home Assistant family; Manrope and system sans are local fallbacks, with no font download. Today uses display type with tabular numerals and a smaller unit; ring and stat values use metric type. The meter name uses title type, explanatory copy uses body type, and chart/status metadata stays compact. Today is sentence case. At compact width, Today becomes (44px), its unit (18px), the ring value (20px), and stat values (19px), with the final meter value (16px).

## Layout

The host fills its dashboard column and establishes an inline-size container. Preserve this order: wrapping identity/live status and calibration chip; ring beside Today; three equal stats; 24 hourly bars; previous seven days; leak/street rows; calibration support; signal footer. Multiple meters stack with a divider. The header uses (24px 24px 28px) padding, a (22px) hero offset and (24px) gap; the ring is (132px) square. The chart is (140px) high with (4px) gaps; the daily strip has seven equal columns and (30px) plots.

At container width ≤ (400px), use mobile gutters, a (104px) ring, (16px) hero gap, (3px) hourly gaps and (5px) daily gaps. The card supports a (360px) viewport without assuming a fixed card width. Forms retain two flexible columns; unit choices fill up to (320px). Use logical text alignment and spacing. Home Assistant locale, time format and timezone govern displayed numbers, clocks and calendar history.

## Elevation & Depth

The card takes Home Assistant's card shadow, defaulting to none, and its border width, defaulting to (1px). Quiet rules, tinted status panels and the translucent wave establish depth. The live dot's expanding halo communicates reception; selected units use an inset accent underline, not extra floating surfaces.

## Shapes

Use the theme's card radius, rounded status panels, compact rounded controls and pill calibration chips. Hourly and daily bars have small rounded ends; missing observations use diagonal hatching. The circular ring uses a (12px) stroke with rounded progress ends. The dial guide is inline SVG, not a raster asset.

## Components

The sidecar holds drop-in previews and exact focus, state, motion and source details. Save reading uses an accent border and tinted fill with hover/active steps; disabled controls are visibly muted. Fields have permanent labels, a muted border and error treatment. Unit radios form a contiguous segmented control. All form targets have a minimum height of (44px).

Hourly bars expose time and usage by hover, keyboard focus or tap, backed by a disclosure containing values tables. Hatched gaps remain separate from observed zero. The usual-day ring shows a neutral learning state until history supports comparison; raw readings remain pulses. Leak and street rows combine icon, text and tint. Calibrated meters disclose check readings; uncalibrated or disputed calibration exposes the guide and form. Read-now adds a timed callout. Waiting, unavailable and encrypted states retain truthful diagnostics.

## Do's and Don'ts

- **Do** preserve the approved hierarchy and compact layout in both themes.
- **Do** retain visible focus, semantic labels, table alternatives and reduced-motion behavior.
- **Do** preserve raw pulses, missing observations and unavailable diagnostics.
- **Don't** replace Home Assistant theme, locale or timezone with fixture settings.
- **Don't** infer zero use from missed reception or invent a usual-day percentage while learning.
- **Don't** add external fonts, image services or unrelated brand rules to this dashboard card.
