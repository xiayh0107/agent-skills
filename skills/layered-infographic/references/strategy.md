# Per-layer strategy router

The core idea: **don't pick one rendering route for the whole image — choose the
best route per layer, then composite all layers into one layered file.** A layer
container (SVG `<g>` groups, or PSD layers) happily holds *both* vector and raster.
Raster-only layers are fine, as long as the file stays layered.

## What goes in which layer

| Layer content | Best route | Form | Why |
|---|---|---|---|
| Title / body text / labels / formulas / data values | vector `<text>` in SVG | vector | must be exact + editable (esp. Chinese, math); raster text garbles |
| Hero visual / background / illustration / texture | gpt-image-2 (`imagegen` skill) | raster `<image>` | looks far better than hand-drawn vector |
| Foreground subject / element that will move | gpt-image-2 on chroma-key → local de-key | transparent PNG | gpt-image-2 has NO native transparency |
| Data-driven graphics (bars, lines, proportions) | chart lib (Vega-Lite / Observable Plot / D3) → SVG | vector | meaningful + re-data-able, and the lib makes it pretty |
| Dense styled layout block | HTML/CSS → headless render (Playwright/satori) | raster `<image>` | CSS flex/grid = flexible layout, not rigid coords |

## The design rule (do not violate)

**Vectorize ONLY what must be exact, edited, or data-driven** — i.e. text, formulas,
data labels, and data charts. **Everything decorative or illustrative → raster** from
gpt-image-2 (or CSS). Hand-drawing mountains, arrows, and decorative boxes as SVG paths
makes the result *uglier* and pins elements to fixed coordinates → rigid layout. Keep
any SVG you author thin: a layout grid, real text, and `<image>` slots.

## Always export two forms

- **Layered SVG** — the "live" file: vector text stays editable, palette/typography
  centralized in `<style>` tokens, raster layers via `<image>`, `<g id="layer-...">` = layers.
- **Multi-layer PSD** — handoff for Photoshop/designers: every layer (raster or
  rasterized-vector) becomes an independently editable named layer.

## Editability switches to build in

1. **Design tokens**: put all colors / font-sizes / weights in CSS classes in the SVG
   `<style>` block (e.g. `.t-title`, `.t-cap`). Swapping a palette = editing one place.
2. **Named layers**: organize as `<g id="layer-bg">`, `<g id="layer-art">`,
   `<g id="layer-text">` … This naming is what the split + PSD scripts key on.
