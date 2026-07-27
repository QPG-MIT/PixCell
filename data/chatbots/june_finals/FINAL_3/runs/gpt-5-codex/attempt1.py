#!/usr/bin/env python3
"""GDS reconstruction generated from the example target image."""

from __future__ import annotations

import sys
from pathlib import Path

import gdstk

from rects_data import RECTANGLES


LAYER = 1
DATATYPE = 0


def build_library() -> gdstk.Library:
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("codex_reconstruction")
    for xa, y_top, xb, y_bot in RECTANGLES:
        if xb <= xa or y_top <= y_bot:
            continue
        cell.add(gdstk.rectangle((xa, y_bot), (xb, y_top), layer=LAYER, datatype=DATATYPE))
    return lib


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_suffix(".gds")
    out.parent.mkdir(parents=True, exist_ok=True)
    build_library().write_gds(str(out))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
