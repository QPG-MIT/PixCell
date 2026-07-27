"""FINAL_7: stadium-ring device, attempt 2 (parametric tier).

Fixes vs attempt 1 (IoU 0.760):
- ring rebuilt as constant-width band (w 0.52) extruded along a racetrack centerline
  with quarter-ellipse corners (the corner crescents dominated attempt 1's error)
- arms re-sloped: they descend from the side walls to the bars (not rise)
- inner-wall pockets added; wedge shrunk to the measured bulge
"""

import math
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def rect(c, x1, y1, x2, y2):
    r = c << gf.components.rectangle(size=(round(x2 - x1, 4), round(y2 - y1, 4)), layer=LAYER)
    r.move((round(x1, 4), round(y1, 4)))
    return r


def racetrack_centerline(x1, x2, y_half, rx, ry, n=40):
    """Closed racetrack: straights on all four sides, quarter-ellipse corners."""
    cx1, cx2 = x1 + rx, x2 - rx
    cy = y_half - ry
    pts = []
    pts.append((cx1, y_half))
    pts.append((cx2, y_half))
    for i in range(1, n + 1):  # top-right corner: 90 -> 0 deg
        th = math.pi / 2 * (1 - i / n)
        pts.append((cx2 + rx * math.cos(th), cy + ry * math.sin(th)))
    pts.append((x2, -cy))
    for i in range(1, n + 1):  # bottom-right: 0 -> -90
        th = -math.pi / 2 * (i / n)
        pts.append((cx2 + rx * math.cos(th), -cy + ry * math.sin(th)))
    pts.append((cx1, -y_half))
    for i in range(1, n + 1):  # bottom-left: -90 -> -180
        th = -math.pi / 2 * (1 + i / n)
        pts.append((cx1 + rx * math.cos(th), -cy + ry * math.sin(th)))
    pts.append((x1, cy))
    for i in range(1, n + 1):  # top-left: 180 -> 90
        th = math.pi / 2 * (2 - i / n)
        pts.append((cx1 + rx * math.cos(th), cy + ry * math.sin(th)))
    return pts


@gf.cell
def stadium_device_v2() -> gf.Component:
    c = gf.Component()

    # --- ring: constant-width band on racetrack centerline ---
    # outer 0..3.0 x, +/-2.75 y; band 0.52 -> centerline inset 0.26
    pts = racetrack_centerline(0.26, 2.74, 2.49, 0.80, 1.45)
    c << gf.path.extrude(gf.Path(pts), cross_section=xs(0.52))

    # --- slotted bars ---
    for sign in (1, -1):
        y1, y2, y3, y4 = 0.395 * sign, 0.635 * sign, 1.185 * sign, 1.431 * sign
        lo12, hi12 = min(y1, y2), max(y1, y2)
        lo34, hi34 = min(y3, y4), max(y3, y4)
        lo23, hi23 = min(y2, y3), max(y2, y3)
        rect(c, 1.052, lo12, 1.944, hi12)
        rect(c, 1.052, lo34, 1.944, hi34)
        for rx1, rx2 in [(1.052, 1.116), (1.441, 1.553), (1.880, 1.944)]:
            rect(c, rx1, lo23, rx2, hi23)

    # --- central wedges (wall bulges) ---
    wl = c << gf.components.taper(length=0.13, width1=1.10, width2=0.012, layer=LAYER)
    wl.move((0.51, 0.0))
    wr = c << gf.components.taper(length=0.13, width1=0.012, width2=1.10, layer=LAYER)
    wr.move((2.36, 0.0))

    # --- arms: wall (low) up to bar rung, both sides/mirrors ---
    for sgn_y in (1, -1):
        for left in (True, False):
            if left:
                p = [(0.50, 0.44 * sgn_y), (0.80, 0.74 * sgn_y), (1.07, 0.97 * sgn_y)]
            else:
                p = [(2.50, 0.44 * sgn_y), (2.20, 0.74 * sgn_y), (1.93, 0.97 * sgn_y)]
            c << gf.path.extrude(gf.Path(p), cross_section=xs(0.24))

    return c


if __name__ == "__main__":
    component = stadium_device_v2()
    out = Path(__file__).parent / "attempt2.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
