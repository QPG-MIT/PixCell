"""FINAL_2: 1x4 MMI splitter, attempt 2 (parametric tier).

vs attempt 1 (IoU 0.9914): per-port top heights, wider taper feet, stub trim,
and anchors placed at the target's actual frame specks.
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

PORTS = [(5.44, 4.110), (9.62, 4.145), (15.04, 4.145), (19.50, 4.145)]


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
def mmi_1x4_v2() -> gf.Component:
    c = gf.Component()

    rect(c, 2.76, -2.348, 22.22, 1.40)

    for cx, top in PORTS:
        vtaper(c, cx, 2.75, top, 1.246, 1.246)
        vtaper(c, cx, 1.38, 2.75, 2.52, 1.246)

    vtaper(c, 12.49, -3.27, -2.34, 1.18, 2.42)

    # anchors at the target's actual frame specks
    rect(c, 3.66, 4.986, 3.70, 4.996)
    rect(c, 0.0, -4.996, 0.06, -4.986)
    rect(c, 24.99, -2.56, 25.0, -2.52)

    return c


if __name__ == "__main__":
    component = mmi_1x4_v2()
    out = Path(__file__).parent / "attempt2.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
