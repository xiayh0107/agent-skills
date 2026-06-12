---
name: layered-infographic
description: "Build editable, LAYERED infographics / posters / 科研信息图 / 教学图 / 封面图 by composing exact vector text with gpt-image-2 raster art into a layered SVG plus a real multi-layer PSD. Use when the user wants a polished infographic, explainer, poster, journal-style cover, or 信息图/教学图/封面图 that must keep editable text (Chinese, formulas, data labels) and replaceable/regenerable art — and wants a layered, re-editable deliverable (SVG + PSD), even if some layers are raster. Do NOT use for a single standalone image (use the imagegen skill directly) or for pure boxes-and-arrows technical diagrams (use a diagram tool)."
---

# Layered Infographic (SVG skeleton + gpt-image-2 art → SVG + PSD)

Compose an infographic as **layers**: precise vector text where text must be exact and
editable, gpt-image-2 raster where the visual must look good — then ship a layered SVG
(the "live" file) **and** a real multi-layer PSD (designer handoff). A layer container
holds both vector and raster; raster-only layers are fine as long as the file is layered.

**Read `references/strategy.md` first** for the per-layer router and the one hard rule:
*vectorize only text / data / exact things; everything decorative → raster.* Hand-drawing
decorative vector shapes makes the result uglier and the layout rigid — don't.

## Dependencies (check once per session)

- **imagegen skill** (`~/.claude/skills/imagegen/`) — generates the art layers via gpt-image-2,
  and de-keys chroma for transparent cutouts. Load its env before generating.
- **`rsvg-convert`** — renders SVG → PNG (layer splitting + previews). `which rsvg-convert`.
- **node + PSD deps** — for the PSD export only. Once: `npm --prefix ~/.claude/skills/layered-infographic/scripts install`.

## Workflow

1. **Plan layers.** From the user's content + a reference (if any), decide the layer stack
   and which route produces each (see `references/strategy.md`). Typical:
   `layer-bg` (cards/background) · `layer-art` (gpt-image-2 imagery) · `layer-text`
   (titles/labels/formulas) · optional `layer-annotations` (arrows, chart, nodes).

2. **Author the SVG skeleton.** Write a single SVG, `viewBox="0 0 W H"`:
   - Centralize palette + type as CSS classes in `<style>` (tokens — see `references/palettes.md`).
   - Put **every** visual element inside a top-level `<g id="layer-...">` group; only
     `<style>`/`<defs>` sit outside. (The split/PSD scripts key on these group ids.)
   - Real text as `<text>` (exact, editable). Keep hand-drawn vector minimal.
   - Reserve art slots as `<image ... preserveAspectRatio="xMidYMid slice"
     xlink:href="asset://assets/<name>.png"/>` (declare `xmlns:xlink` on `<svg>`).
   - Card backgrounds must be drawn **before** the art layer (z-order). Put the canvas
     background inside `layer-bg`, not as a bare top-level `<rect>`.

3. **Generate the art** with the imagegen skill, into `assets/`:
   - Backgrounds / illustrations: `image_gen.py generate ...`
   - Transparent subjects: generate on flat `#00ff00`, then `remove_chroma_key.py`
     (gpt-image-2 has no native transparency).
   - For "progressively noisier" / diffusion-style bands, generate ONE clean base image
     and overlay procedural noise (SVG `feTurbulence` rect at increasing `opacity`) — don't
     spend an API call per frame.

4. **Fill slots** (embed assets as base64 so the file is self-contained):
   ```bash
   python ~/.claude/skills/layered-infographic/scripts/embed_assets.py \
     skeleton.svg --out final.svg --base . --max-width 1400
   ```

5. **Render the composite** and view it; validate text/layout/invariants:
   ```bash
   rsvg-convert -w 2240 final.svg -o final.png
   ```

6. **Export the layered deliverables** (always do both):
   ```bash
   # split into aligned per-layer PNGs + a PSD manifest
   python ~/.claude/skills/layered-infographic/scripts/split_svg_layers.py \
     final.svg --out-dir build --width 1120 --psd-name myfig.psd
   # assemble the real multi-layer PSD (named layers + flattened preview)
   node ~/.claude/skills/layered-infographic/scripts/build_psd.mjs build/psd_manifest.json .
   ```
   Result: `final.svg` (editable text + replaceable art), `final.png` (publish), `myfig.psd`
   (Photoshop, independently editable named layers).

## Conventions the scripts rely on

- Top-level groups named `<g id="layer-NAME">` → PSD layer "NAME", in document order.
- Slots authored as `xlink:href="asset://<relative-path>"` → replaced by `embed_assets.py`.
- A bare full-canvas background `<rect>` is auto-stripped from per-layer renders, but prefer
  wrapping it in `layer-bg`.

## Gotchas (learned)

- gpt-image-2: no `background:transparent`, no PSD output — both are produced by this
  workflow, not the model. Small/dense text garbles → keep it in the vector layer; gpt-image-2
  handles short labels and imagery well.
- PSD must carry a top-level composite or viewers show black (the script handles this).
- Use ASCII layer names; some readers garble non-ASCII legacy names (Photoshop is fine either way).
- imagegen proxy may throw intermittent 429 mid-batch → retry the failed job / lower concurrency.

## References (read on demand)

- `references/strategy.md` — per-layer router + the vectorize-only-text rule + editability switches
- `references/palettes.md` — 科研 palette systems as token sets (Nature / Science / Cell / 医学 …)
