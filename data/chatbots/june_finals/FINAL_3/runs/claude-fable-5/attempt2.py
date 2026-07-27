"""FINAL_3: adiabatic asymmetric directional coupler, attempt 2 (parametric tier).

Fixes vs attempt 1 (IoU 0.809): s-bends rebuilt as gentle-steep-gentle composites
(3 bend_s each) matching the measured tanh-like profile; entry tapers retimed.
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER, radius=5.0, radius_min=0.05)


def place(c, comp, x, y):
    r = c << comp
    r.move((x, y))
    return r


def composite_sbend(c, x, y, dy_total, w, dx_total=12.5):
    """Gentle-steep-gentle S: 25/50/25 vertical split over 40/20/40 horizontal."""
    d1, d2, d3 = 0.42 * dx_total, 0.16 * dx_total, 0.42 * dx_total
    e1, e2, e3 = 0.18 * dy_total, 0.64 * dy_total, 0.18 * dy_total
    b1 = place(c, gf.components.bend_s(size=(d1, round(e1, 3)), cross_section=xs(w)), x, y)
    b2 = place(c, gf.components.bend_s(size=(d2, round(e2, 3)), cross_section=xs(w)), x + d1, y + round(e1, 3))
    b3 = place(c, gf.components.bend_s(size=(d3, round(e3, 3)), cross_section=xs(w)), x + d1 + d2, y + round(e1, 3) + round(e2, 3))


@gf.cell
def adc_v2() -> gf.Component:
    c = gf.Component()

    # --- top arm ---
    place(c, gf.components.straight(length=8.0, cross_section=xs(0.304)), 0.0, 1.735)
    place(c, gf.components.taper(length=11.0, width1=0.304, width2=0.460, layer=LAYER), 8.0, 1.735)
    composite_sbend(c, 19.0, 1.735, -1.510, 0.470)
    place(c, gf.components.taper(length=55.5, width1=0.488, width2=0.320, layer=LAYER), 31.5, 0.225)
    composite_sbend(c, 87.0, 0.222, 1.612, 0.340, dx_total=14.5)
    place(c, gf.components.straight(length=18.5, cross_section=xs(0.310)), 101.5, 1.834)

    # --- bottom arm ---
    place(c, gf.components.straight(length=8.0, cross_section=xs(0.300)), 0.0, -1.710)
    place(c, gf.components.taper(length=11.0, width1=0.300, width2=0.204, layer=LAYER), 8.0, -1.710)
    composite_sbend(c, 19.0, -1.712, 1.477, 0.204)
    place(c, gf.components.taper(length=55.5, width1=0.204, width2=0.290, layer=LAYER), 31.5, -0.235)
    composite_sbend(c, 87.0, -0.237, -1.595, 0.310, dx_total=14.5)
    place(c, gf.components.straight(length=18.5, cross_section=xs(0.300)), 101.5, -1.832)

    return c


if __name__ == "__main__":
    component = adc_v2()
    out = Path(__file__).parent / "attempt2.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
