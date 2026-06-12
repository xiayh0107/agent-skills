---
name: imagegen
description: "Generate or edit raster images (photos, illustrations, game sprites, textures, UI/product mockups, hero banners, logo concepts, infographics, transparent cutouts) via the GPT Image API CLI. Use when the user asks to generate, create, draw, or edit an image/picture/photo — including Chinese requests like 生成图片、画一张图、做张图、配图、改图、P图、抠图、透明背景、产品图、封面图. Do NOT use for technical/architecture diagrams or flowcharts (架构图/流程图/时序图 — those are diagram tools' job), for editing existing SVG/vector assets, or when the visual is better built directly in HTML/CSS/canvas."
---

# Image Generation Skill (GPT Image CLI)

Generates or edits raster images using the GPT Image API via the bundled CLI at
`~/.claude/skills/imagegen/scripts/image_gen.py`. Default model: `gpt-image-2`.

## Setup (run once per session, before any generation)

The CLI needs `OPENAI_API_KEY` (and optionally `OPENAI_BASE_URL`). Resolve in this order:

1. Already exported in the environment → use as-is.
2. `./.env` in the current project → `set -a; source .env; set +a`
3. Skill-local fallback → `set -a; source ~/.claude/skills/imagegen/.env; set +a`

If none exists, ask the user to set `OPENAI_API_KEY` locally. Never ask them to paste the key in chat.

Dependencies: `openai` (required), `pillow` (only for chroma-key removal / downscaling). If missing, install with the project's package manager (`uv pip install openai pillow` preferred).

Convenience variable used in all examples:

```bash
IMAGE_GEN="$HOME/.claude/skills/imagegen/scripts/image_gen.py"
```

## Subcommands

- `generate` — new image from a prompt
- `edit` — edit one or more existing images (`--image`, repeatable; optional `--mask`)
- `generate-batch` — many different prompts concurrently from a JSONL file (requires `--out-dir`)

Rules:
- Never modify `scripts/image_gen.py`; never write one-off SDK runner scripts.
- `--n` is for variants of ONE prompt; distinct assets need distinct prompts (separate calls or `generate-batch` jobs).
- Reruns fail if the target file exists unless `--force`. Don't overwrite existing assets the user didn't ask to replace — use versioned siblings (`hero-v2.png`).

## Workflow

1. Ensure env is loaded (Setup above).
2. Decide intent: `generate` (new image, or reference-guided) vs `edit` (preserve parts of an existing image).
3. Collect inputs: prompt, exact text (verbatim), constraints/avoid list, input images with explicit roles (reference / edit target / insert).
4. Augment the prompt per `references/prompting.md`: structure as scene → subject → details → constraints. If the user's prompt is detailed, normalize it without adding creative content; if generic, add only what materially helps. For edits, state invariants explicitly ("change only X; keep Y unchanged") and repeat them on every iteration.
5. Run the CLI. Use `--quality low --size 1024x1024` for drafts/iterations; `medium`/`high` for finals, dense text, or identity-sensitive edits.
6. View the output image, validate subject/style/composition/text accuracy/invariants. Iterate with single targeted changes.
7. Save finals: project-bound assets go in the workspace (convention: `output/imagegen/`) and update any consuming code; scratch files in `tmp/imagegen/` (clean up after). Always report final saved path(s) and the final prompt used.

## Quick examples

```bash
# Draft
python "$IMAGE_GEN" generate --prompt "..." --quality low --size 1024x1024 --out output/imagegen/draft.png

# Final 2K landscape
python "$IMAGE_GEN" generate --prompt "..." --quality high --size 2048x1152 --out output/imagegen/hero.png

# Edit with invariants
python "$IMAGE_GEN" edit --image input.png \
  --prompt "Replace only the background with a warm sunset; keep the product and its edges unchanged" \
  --out output/imagegen/sunset-edit.png

# Batch (one JSONL line per distinct asset)
python "$IMAGE_GEN" generate-batch --input tmp/imagegen/prompts.jsonl --out-dir output/imagegen/batch --concurrency 5
```

`--dry-run` prints the API payload without network/key — use it to validate arguments when debugging.

## gpt-image-2 parameters

- `quality`: `low` | `medium` | `high` | `auto` (default medium)
- `size`: `auto` or `WIDTHxHEIGHT` — max edge ≤ 3840, both edges multiples of 16, ratio ≤ 3:1, total pixels 655,360–8,294,400. Popular: `1024x1024`, `1536x1024`, `1024x1536`, `2048x1152`, `3840x2160` (4K).
- Do NOT pass `--input-fidelity` with gpt-image-2 (always high). Do NOT pass `--background transparent` with gpt-image-2 (unsupported).
- Square is fastest; expect ~1–2 min per image.

## Transparent background requests

`gpt-image-2` cannot output native transparency. Two paths:

**Default — chroma-key + local removal** (simple opaque subjects):
1. Generate the subject on a perfectly flat solid chroma-key background (`#00ff00`; use `#ff00ff` for green subjects). Prompt: "perfectly flat solid #00ff00 background, no shadows/gradients/reflections, crisp edges, generous padding, do not use #00ff00 in the subject".
2. Remove locally:
   ```bash
   python ~/.claude/skills/imagegen/scripts/remove_chroma_key.py \
     --input <source> --out <final.png> \
     --auto-key border --soft-matte --transparent-threshold 12 --opaque-threshold 220 --despill
   ```
3. Validate alpha channel, transparent corners, no key-color fringe. Thin fringe → retry once with `--edge-contract 1`.

**Native transparency — `gpt-image-1.5`** (complex subjects: hair, fur, glass, smoke, translucency, soft shadows):
```bash
python "$IMAGE_GEN" generate --model gpt-image-1.5 --prompt "..." --background transparent --output-format png --out <final.png>
```
This is a model downgrade from gpt-image-2 — ask the user before switching unless they already requested gpt-image-1.5 or native transparency explicitly.

## References (read on demand)

- `references/prompting.md` — shared prompting principles, use-case taxonomy, prompt schema
- `references/sample-prompts.md` — copy/paste prompt recipes by asset type
- `references/cli.md` — full CLI flag reference (masks, downscaling, batch JSONL overrides)
- `references/image-api.md` — API parameter reference
