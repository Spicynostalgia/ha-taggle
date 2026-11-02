# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Home Assistant users checking household water use and calibrating their own Taggle transmitter from physical dial readings.

## Product Purpose

A local dashboard card connects observed transmitter usage, reception, calibration and possible-leak hints. The receiver supplies MQTT entities; Home Assistant Recorder supplies recorded daily usage history.

## Capabilities and Constraints

The dependency-free custom element supports entity mappings, device discovery, multiple meters, neighbourhood aggregates and dial-reading controls. Preserve raw pulses before calibration, missing observations, encrypted-meter diagnostics and unavailable/waiting states. No external services or fonts are required.

## Brand Commitments

The user approved a water-wave header, usual-day ring, dominant Today value, three stats, hourly chart and seven-day strip, status rows and small signal footer. Home Assistant theme, locale and timezone take precedence over fallback styling.

## Accessibility & Inclusion

Support keyboard and screen-reader use, reduced motion, light and dark themes, and a 360 px phone viewport.
