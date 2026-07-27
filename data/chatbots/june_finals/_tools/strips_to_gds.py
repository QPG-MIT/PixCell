"""Reconstruction-tier GDS builder: one rectangle per traced strip run.

Usage: python strips_to_gds.py <strips_data.py> <out.gds>
"""

import sys
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)


def build(strips) -> gf.Component:
    c = gf.Component()
    for y1, y2, xa, xb in strips:
        w, h = round(xb - xa, 4), round(abs(y1 - y2), 4)
        if w <= 0 or h <= 0:
            continue
        r = c << gf.components.rectangle(size=(w, h), layer=LAYER)
        r.move((xa, min(y1, y2)))
    return c


if __name__ == "__main__":
    data_file, out = Path(sys.argv[1]), Path(sys.argv[2])
    ns = {}
    exec(data_file.read_text(), ns)
    component = build(ns["STRIPS"])
    component.write_gds(str(out))
    print(f"wrote {out}")
