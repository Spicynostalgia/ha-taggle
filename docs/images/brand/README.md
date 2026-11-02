# ha-taggle artwork

**Water becomes signal.** The open edge of the droplet becomes a pair of radio arcs. Quiet meter, antenna, receiver and house drawings share that curved line language. No third-party logos, identifying data, external resources, filters or animation.

The palette extends `../setup-diagram.svg`, `../signal-flow.svg` and the previous social preview: water blue `#167b9c`, slate `#203744`, mist `#f7fafb`, pale sage `#d7e7df`. Dark artwork uses deep slate `#112c39` and soft water blue `#8fcddd`. Typography uses `-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif`; no font downloads, embeds or `foreignObject`. Each SVG has an accessible title and description. The original SVGs are the editable sources.

[Open the preview](preview.html) to see every asset on light and dark backgrounds, including small marks and mobile compositions. Each preview has SVG and PNG links. The project README is intentionally untouched.

## Files

Dimensions below are logical SVG dimensions. Every adjacent PNG is rendered at **2×** (including the social preview in this directory). The transparent logo/mark PNGs retain alpha. PNG optimization is lossless.

| SVG source | Logical size | PNG at 2× |
| --- | --- | --- |
| [logo.svg](logo.svg) | 520 × 128 | [logo.png](logo.png) · 1040 × 256 |
| [logo-dark.svg](logo-dark.svg) | 520 × 128 | [logo-dark.png](logo-dark.png) · 1040 × 256 |
| [logo-mark.svg](logo-mark.svg) | 128 × 128 | [logo-mark.png](logo-mark.png) · 256 × 256 |
| [logo-mark-dark.svg](logo-mark-dark.svg) | 128 × 128 | [logo-mark-dark.png](logo-mark-dark.png) · 256 × 256 |
| [hero-light.svg](hero-light.svg) | 1600 × 520 | [hero-light.png](hero-light.png) · 3200 × 1040 |
| [hero-dark.svg](hero-dark.svg) | 1600 × 520 | [hero-dark.png](hero-dark.png) · 3200 × 1040 |
| [hero-mobile-light.svg](hero-mobile-light.svg) | 720 × 600 | [hero-mobile-light.png](hero-mobile-light.png) · 1440 × 1200 |
| [hero-mobile-dark.svg](hero-mobile-dark.svg) | 720 × 600 | [hero-mobile-dark.png](hero-mobile-dark.png) · 1440 × 1200 |
| [how-it-works-light.svg](how-it-works-light.svg) | 1600 × 300 | [how-it-works-light.png](how-it-works-light.png) · 3200 × 600 |
| [how-it-works-dark.svg](how-it-works-dark.svg) | 1600 × 300 | [how-it-works-dark.png](how-it-works-dark.png) · 3200 × 600 |
| [how-it-works-mobile-light.svg](how-it-works-mobile-light.svg) | 720 × 824 | [how-it-works-mobile-light.png](how-it-works-mobile-light.png) · 1440 × 1648 |
| [how-it-works-mobile-dark.svg](how-it-works-mobile-dark.svg) | 720 × 824 | [how-it-works-mobile-dark.png](how-it-works-mobile-dark.png) · 1440 × 1648 |
| [button-install-addon-light.svg](button-install-addon-light.svg) | 260 × 56 | [button-install-addon-light.png](button-install-addon-light.png) · 520 × 112 |
| [button-install-addon-dark.svg](button-install-addon-dark.svg) | 260 × 56 | [button-install-addon-dark.png](button-install-addon-dark.png) · 520 × 112 |
| [button-add-card-hacs-light.svg](button-add-card-hacs-light.svg) | 260 × 56 | [button-add-card-hacs-light.png](button-add-card-hacs-light.png) · 520 × 112 |
| [button-add-card-hacs-dark.svg](button-add-card-hacs-dark.svg) | 260 × 56 | [button-add-card-hacs-dark.png](button-add-card-hacs-dark.png) · 520 × 112 |
| [button-read-wiki-light.svg](button-read-wiki-light.svg) | 260 × 56 | [button-read-wiki-light.png](button-read-wiki-light.png) · 520 × 112 |
| [button-read-wiki-dark.svg](button-read-wiki-dark.svg) | 260 × 56 | [button-read-wiki-dark.png](button-read-wiki-dark.png) · 520 × 112 |
| [button-report-council-light.svg](button-report-council-light.svg) | 260 × 56 | [button-report-council-light.png](button-report-council-light.png) · 520 × 112 |
| [button-report-council-dark.svg](button-report-council-dark.svg) | 260 × 56 | [button-report-council-dark.png](button-report-council-dark.png) · 520 × 112 |
| [social-preview.svg](social-preview.svg) | 1280 × 640 | [social-preview.png](social-preview.png) · 2560 × 1280 |

`logo.svg` is the mark plus wordmark; `logo-mark.svg` is the standalone mark, designed for 32–256 px. Use their dark counterparts on dark backgrounds. Logos are transparent; heroes, diagrams and buttons have explicit theme backgrounds.

The wide hero and diagram retain their required viewBoxes. Mobile alternatives give small screens larger copy and a vertical flow. They contain the same message. The responsive markup below selects them at 480 px and below.

`../social-preview.svg` mirrors `social-preview.svg` here. `../social-preview.png` is **1280 × 640**, ready for the repository social-preview upload; `social-preview.png` here is the requested **2560 × 1280** 2× export. Social cards have one fixed light palette because social consumers do not select a color scheme.

## Exact root README markup

These paths are relative to the **repository root README**, not this file. Paste the desired blocks into that README. GitHub serves these self-contained SVGs as images; color-scheme selection happens in the surrounding `<picture>`, not inside the SVG. PNG fallback is available by replacing each `.svg` extension with `.png` and keeping the display widths below.

### Hero (desktop, mobile, light and dark)

```html
<picture>
  <source media="(max-width: 480px) and (prefers-color-scheme: dark)" srcset="docs/images/brand/hero-mobile-dark.svg">
  <source media="(max-width: 480px)" srcset="docs/images/brand/hero-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/brand/hero-dark.svg">
  <img src="docs/images/brand/hero-light.svg" width="1600" alt="ha-taggle. Your Taggle water meter, live in Home Assistant. Receive-only · local · RTL-SDR · open source.">
</picture>
```

### How it works (desktop, mobile, light and dark)

```html
<picture>
  <source media="(max-width: 480px) and (prefers-color-scheme: dark)" srcset="docs/images/brand/how-it-works-mobile-dark.svg">
  <source media="(max-width: 480px)" srcset="docs/images/brand/how-it-works-mobile-light.svg">
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/brand/how-it-works-dark.svg">
  <img src="docs/images/brand/how-it-works-light.svg" width="1600" alt="Meter → Taggle radio → RTL-SDR + ha-taggle → Home Assistant. Receive-only, local processing.">
</picture>
```

For a wide-only composition, omit the first two `<source>` elements in either block. The wide hero remains readable at 360 px, although the mobile composition gives its sub-line more space. Use the mobile diagram for readable step labels on a phone.

### Logo and standalone mark

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/brand/logo-dark.svg">
  <img src="docs/images/brand/logo.svg" width="260" alt="ha-taggle">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/images/brand/logo-mark-dark.svg">
  <img src="docs/images/brand/logo-mark.svg" width="64" alt="ha-taggle droplet and radio mark">
</picture>
```

### Linked buttons

Render each at **260 × 56** CSS pixels. These are artwork, so the surrounding anchor supplies the action. The destinations below reuse the current repository's install, HACS, wiki and compatibility-report routes. Installation links open the relevant flow; the user completes installation there.

```html
<a href="https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FSpicynostalgia%2Fha-taggle">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/brand/button-install-addon-dark.svg">
    <img src="docs/images/brand/button-install-addon-light.svg" width="260" height="56" alt="Install the add-on">
  </picture>
</a>
```

```html
<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=Spicynostalgia&amp;repository=ha-taggle&amp;category=plugin">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/brand/button-add-card-hacs-dark.svg">
    <img src="docs/images/brand/button-add-card-hacs-light.svg" width="260" height="56" alt="Add the card (HACS)">
  </picture>
</a>
```

```html
<a href="https://github.com/Spicynostalgia/ha-taggle/wiki">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/brand/button-read-wiki-dark.svg">
    <img src="docs/images/brand/button-read-wiki-light.svg" width="260" height="56" alt="Read the wiki">
  </picture>
</a>
```

```html
<a href="https://github.com/Spicynostalgia/ha-taggle/issues/new/choose">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/brand/button-report-council-dark.svg">
    <img src="docs/images/brand/button-report-council-light.svg" width="260" height="56" alt="Report your council">
  </picture>
</a>
```

### Social preview

Social cards do not support `<picture>` theme switching. Upload `docs/images/social-preview.png` in the repository social-preview setting. For an inline copy:

```html
<img src="docs/images/brand/social-preview.svg" width="1280" alt="ha-taggle. Your Taggle water meter, live in Home Assistant. Receive-only · local · RTL-SDR · open source.">
```

## Rendering and verification

`render.mjs` renders every SVG with headless Chromium at 2×, copies the social SVG to the parent directory and recreates its 1× social PNG there. It also checks all SVG text bounding boxes for clipping and losslessly recompresses PNG image data. It requires Node.js and an existing Playwright installation with Chromium; it leaves the SVG sources in this directory unchanged and does not install dependencies.

```sh
node docs/images/brand/render.mjs
```

For a separately installed browser/module or review captures:

```sh
PLAYWRIGHT_MODULE=/absolute/path/to/playwright/index.mjs \
CHROMIUM_EXECUTABLE=/absolute/path/to/chromium \
REVIEW_DIR=/tmp/ha-taggle-brand-review \
node docs/images/brand/render.mjs
```

On a minimal Linux host, configure Fontconfig to use installed system-compatible sans fonts before rendering. The supplied PNGs were rendered with Liberation Sans as the Arial-compatible fallback. SVG text remains live and may vary slightly by operating system.

Verified with headless Chromium: all 21 SVGs and PNG dimensions; no clipped SVG text; exact wide-asset captures at 880 px and 360 px; full preview at both widths without horizontal overflow; mobile hero and diagram compositions; transparent marks at small sizes; light and dark families. The PNG compressor verifies identical decompressed image data. Button text contrast is **4.61:1** for the blue light primary, **11.84:1** for the light secondary, **8.28:1** for the dark primary and **13.87:1** for the dark secondary (WCAG AA ≥4.5:1). Hero/diagram text uses the same foregrounds, with muted copy at 5.51:1 light and 8.82:1 dark.
