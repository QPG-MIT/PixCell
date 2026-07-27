"""FINAL_2: 1x4 MMI splitter (25 x 10 um), attempt 1 (parametric tier).

- body rect x [2.76, 22.22], y [-2.348, +1.40]
- 4 output ports (w 1.246 straights from +4.14 to +2.70, tapers 1.246 -> 2.46 into body)
  at centers x = 5.44, 9.62, 15.04, 19.50 (measured, non-uniform pitch)
- input stub: inverted taper, w 2.33 at body to 1.21 at y -3.30, centered x 12.49
- bbox extent anchors (target bbox comes from isolated specks at the frame edges)
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

PORT_X = [5.44, 9.62, 15.04, 19.50]


def rect(c, x1, y1, x2, y2):
    r = c << gf.components.rectangle(size=(round(x2 - x1, 4), round(y2 - y1, 4)), layer=LAYER)
    r.move((round(x1, 4), round(y1, 4)))
    return r


def vtaper(c, cx, y_bot, y_top, w_bot, w_top):
    t = c << gf.components.taper(length=round(y_top - y_bot, 4), width1=w_bot, width2=w_top, layer=LAYER)
    t.rotate(90)
    t.move((cx, y_bot))
    return t


@gf.cell
def mmi_1x4_v1() -> gf.Component:
    c = gf.Component()

    rect(c, 2.76, -2.348, 22.22, 1.40)

    for cx in PORT_X:
        vtaper(c, cx, 2.70, 4.14, 1.246, 1.246)
        vtaper(c, cx, 1.38, 2.70, 2.46, 1.246)

    vtaper(c, 12.49, -3.30, -2.34, 1.21, 2.33)

    # bbox extent anchors
    rect(c, 12.40, 4.976, 12.44, 4.996)
    rect(c, 12.40, -4.996, 12.44, -4.976)
    rect(c, 0.0, -0.02, 0.04, 0.02)
    rect(c, 24.96, -0.02, 25.0, 0.02)

    return c


if __name__ == "__main__":
    component = mmi_1x4_v1()
    out = Path(__file__).parent / "attempt1.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
