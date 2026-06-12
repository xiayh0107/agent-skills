#!/usr/bin/env python3
"""Split a layered SVG into aligned PNGs (one per top-level <g id="..."> group)
and emit a PSD manifest. Layer groups stay transparent; a full-canvas composite
is rendered from the original SVG. Requires `rsvg-convert` on PATH.

Convention: every visual element lives inside a top-level <g id="layer-..."> group;
only <style>/<defs> sit outside. A bare full-canvas background <rect> (if present)
is stripped from per-layer renders so layers keep transparency.
"""
import argparse, json, os, re, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("svg")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--width", type=int, default=None,
                    help="render width in px (default = viewBox width)")
    ap.add_argument("--psd-name", default="output.psd")
    args = ap.parse_args()

    s = open(args.svg, encoding="utf-8").read()
    m = re.search(r"<svg\b[^>]*>", s)
    if not m:
        sys.exit("no <svg> tag found")
    svgtag = m.group(0)
    vb = re.search(r'viewBox="[\d.\- ]*?([\d.]+)\s+([\d.]+)"', svgtag)
    wm = re.search(r'\bwidth="([\d.]+)"', svgtag)
    hm = re.search(r'\bheight="([\d.]+)"', svgtag)
    if vb:
        W, H = float(vb.group(1)), float(vb.group(2))
    elif wm and hm:
        W, H = float(wm.group(1)), float(hm.group(1))
    else:
        sys.exit("cannot determine canvas size (need viewBox or width/height)")

    width = args.width or int(round(W))
    height = int(round(width * H / W))

    gi = s.find('<g id=')
    if gi == -1:
        sys.exit("no <g id=...> layer groups found")
    head = s[:gi]
    # drop one bare full-canvas background rect from per-layer head (keep transparency)
    head_layer = re.sub(
        r'<rect\b[^>]*\bwidth="%g"[^>]*\bheight="%g"[^>]*/>' % (W, H),
        '', head, count=1)

    # depth-aware scan of top-level <g ...> blocks
    layers = []
    j = gi
    svg_end = s.rfind('</svg>')
    while True:
        start = s.find('<g', j)
        if start == -1 or start >= svg_end:
            break
        idm = re.search(r'<g\b[^>]*\bid="([^"]+)"', s[start:start + 300])
        depth, k, end = 0, start, None
        while True:
            ng = s.find('<g', k + 1)
            cg = s.find('</g>', k + 1)
            if cg == -1:
                break
            if ng != -1 and ng < cg:
                depth += 1; k = ng
            else:
                if depth == 0:
                    end = cg + 4; break
                depth -= 1; k = cg
        if end is None:
            break
        gid = idm.group(1) if idm else f"layer{len(layers)}"
        layers.append((gid, s[start:end]))
        j = end

    os.makedirs(args.out_dir, exist_ok=True)
    manifest = {"width": width, "height": height,
                "out": args.psd_name, "layers": []}

    comp = os.path.join(args.out_dir, "00_composite.png")
    subprocess.run(["rsvg-convert", "-w", str(width), args.svg, "-o", comp], check=True)
    manifest["composite"] = os.path.basename(comp)

    for i, (gid, block) in enumerate(layers, 1):
        name = re.sub(r'^layer-', '', gid)
        layer_svg = head_layer + block + "\n</svg>"
        tmp = os.path.join(args.out_dir, f"_{i:02d}_{name}.svg")
        png = os.path.join(args.out_dir, f"{i:02d}_{name}.png")
        open(tmp, "w", encoding="utf-8").write(layer_svg)
        subprocess.run(["rsvg-convert", "-w", str(width), tmp, "-o", png], check=True)
        os.remove(tmp)
        manifest["layers"].append({"name": name, "file": os.path.basename(png)})
        print(f"  layer {i}: {name} -> {png}")

    mpath = os.path.join(args.out_dir, "psd_manifest.json")
    json.dump(manifest, open(mpath, "w"), ensure_ascii=False, indent=2)
    print("manifest:", mpath)


if __name__ == "__main__":
    main()
