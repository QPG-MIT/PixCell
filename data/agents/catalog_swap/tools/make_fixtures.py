"""Build neutral catalog fixtures: cat1..cat8 -> device_bw.png + footprint.json.

Renders each gdsfactory component to the same B&W convention as the FINAL_1..8
fixtures (black = material on layer (1,0), white background, tight bbox), at a
resolution matched to the benchmark rasterizer. Neutral dir names by design:
worker-visible paths must never leak component identity (hint-lint invariant).

Run: .venv/bin/python data/agents/catalog_swap/tools/make_fixtures.py
"""
import json
from pathlib import Path

import gdsfactory as gf
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "data/agents/catalog_swap"

# component id -> (factory name, kwargs)  — identity lives ONLY here and in
# stencils/ (conductor-side); never in worker-visible fixture dirs.
CATALOG = {
    "cat1": ("mzi", {}),
    "cat2": ("ring_single", {}),
    "cat3": ("mmi1x2", {}),
    "cat4": ("mmi2x2", {}),
    "cat5": ("coupler", {}),
    "cat6": ("crossing", {}),
    "cat7": ("spiral", {}),
    "cat8": ("dbr", {"n": 20}),
}

TARGET_LONG_PX = 1600  # long-side pixels, comfortably above benchmark raster res


def render(comp) -> Image.Image:
    polys = []
    for _layer, plist in comp.get_polygons_points(merge=False).items():
        polys.extend(plist)
    xmin, ymin = comp.xmin, comp.ymin
    w, h = comp.xsize, comp.ysize
    scale = TARGET_LONG_PX / max(w, h)
    W, H = int(round(w * scale)) + 2, int(round(h * scale)) + 2
    img = Image.new("L", (W, H), 255)
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for poly in polys:
        pts = [((x - xmin) * scale + 1, H - ((y - ymin) * scale + 1)) for x, y in poly]
        d.polygon(pts, fill=0)
    return img


def main():
    for cid, (name, kw) in CATALOG.items():
        comp = getattr(gf.components, name)(**kw)
        d = OUT / cid
        d.mkdir(parents=True, exist_ok=True)
        render(comp).save(d / "device_bw.png")
        (d / "footprint.json").write_text(json.dumps(
            {"footprint_um": [round(comp.xsize, 3), round(comp.ysize, 3)]}))
        print(f"{cid}: {comp.xsize:.2f} x {comp.ysize:.2f} um -> {d}/device_bw.png")


if __name__ == "__main__":
    main()
