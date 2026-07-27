"""FINAL_7: stadium-ring resonator with slotted bars, attempt 1 (parametric tier).

Measured (3.0 x 5.5 um, 517 px/um x, 141.8 px/um y):
- outer stadium: 0..3.0 x, +/-2.750 y, elliptical corners (rx 1.0, ry 1.6)
- inner hole: 0.518..2.476 x, +/-2.235 y, elliptical corners (rx 0.55, ry 1.5)
- two slotted bars (x 1.052..1.944, y 0.395..1.431 and mirror): rails 0.24, three rungs
- central wedges pointing inward from side walls, four diagonal arms to the bars
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def rect(c, x1, y1, x2, y2):
    r = c << gf.components.rectangle(size=(round(x2 - x1, 4), round(y2 - y1, 4)), layer=LAYER)
    r.move((round(x1, 4), round(y1, 4)))
    return r


def stadium(rx, ry, x1, x2, y_half) -> gf.Component:
    """Rounded rect: straights x1..x2 / +/-y_half with elliptical corners (rx, ry)."""
    s = gf.Component()
    cx1, cx2 = x1 + rx, x2 - rx
    cy = y_half - ry
    rect(s, cx1, -y_half, cx2, y_half)
    rect(s, x1, -cy, x2, cy)
    for ex in (cx1, cx2):
        for ey in (cy, -cy):
            e = s << gf.components.ellipse(radii=(rx, ry), layer=LAYER)
            e.move((ex, ey))
    return s


@gf.cell
def stadium_device_v1() -> gf.Component:
    c = gf.Component()

    outer = stadium(1.0, 1.6, 0.0, 3.0, 2.750)
    hole = stadium(0.552, 1.5, 0.518, 2.476, 2.235)
    ring = gf.boolean(outer, hole, operation="not", layer=LAYER)
    c << ring

    # --- slotted bars (top and bottom) ---
    for sign in (1, -1):
        ys = lambda y: sign * y
        lo, hi = (0.395, 1.431) if sign > 0 else (-1.431, -0.395)
        rect(c, 1.052, ys(0.395) if sign > 0 else -0.635, 1.944, ys(0.635) if sign > 0 else -0.395)
        rect(c, 1.052, ys(1.185) if sign > 0 else -1.431, 1.944, ys(1.431) if sign > 0 else -1.185)
        for rx1, rx2 in [(1.052, 1.116), (1.441, 1.553), (1.880, 1.944)]:
            rect(c, rx1, min(ys(0.635), ys(1.185)), rx2, max(ys(0.635), ys(1.185)))

    # --- central wedges ---
    wl = c << gf.components.taper(length=0.25, width1=1.38, width2=0.012, layer=LAYER)
    wl.move((0.45, 0.0))
    wr = c << gf.components.taper(length=0.25, width1=0.012, width2=1.40, layer=LAYER)
    wr.move((2.30, 0.0))

    # --- diagonal arms ---
    for pts in [
        [(0.52, 0.50), (0.80, 0.78), (1.07, 1.05)],
        [(2.46, 0.48), (2.20, 0.76), (1.93, 1.05)],
        [(0.52, -0.50), (0.80, -0.78), (1.07, -1.05)],
        [(2.46, -0.48), (2.20, -0.76), (1.93, -1.05)],
    ]:
        c << gf.path.extrude(gf.Path(pts), cross_section=xs(0.30))

    return c


if __name__ == "__main__":
    component = stadium_device_v1()
    out = Path(__file__).parent / "attempt1.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
