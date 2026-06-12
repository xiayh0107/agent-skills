#!/usr/bin/env python3
"""Embed raster assets into an SVG's slots, replacing asset:// placeholders with
base64 data URIs (so the SVG is self-contained and rsvg-convert renders offline).

Author image slots as:
    <image x=".." y=".." width=".." height=".."
           preserveAspectRatio="xMidYMid slice"
           xlink:href="asset://assets/ink.png"/>

Then:  python embed_assets.py skeleton.svg --out final.svg --base . --max-width 1200
`--max-width` downscales embedded rasters (needs Pillow) to keep file size sane.
"""
import argparse, base64, io, os, re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg")
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default=".", help="base dir for asset:// paths")
    ap.add_argument("--max-width", type=int, default=0,
                    help="downscale embedded images to this width (0 = keep original)")
    args = ap.parse_args()

    s = open(args.svg, encoding="utf-8").read()
    cache = {}

    def datauri(rel):
        data = open(os.path.join(args.base, rel), "rb").read()
        if args.max_width:
            try:
                from PIL import Image
                im = Image.open(io.BytesIO(data))
                if im.width > args.max_width:
                    h = round(im.height * args.max_width / im.width)
                    im = im.convert("RGBA").resize((args.max_width, h), Image.LANCZOS)
                    buf = io.BytesIO(); im.save(buf, "PNG"); data = buf.getvalue()
            except ImportError:
                pass
        return "data:image/png;base64," + base64.b64encode(data).decode()

    def repl(mt):
        rel = mt.group(2)
        if rel not in cache:
            cache[rel] = datauri(rel)
        return mt.group(1) + cache[rel] + mt.group(3)

    s = re.sub(r'(href=")asset://([^"]+)(")', repl, s)
    open(args.out, "w", encoding="utf-8").write(s)
    print(f"embedded {len(cache)} asset(s) -> {args.out}")


if __name__ == "__main__":
    main()
