"""FINAL_3: adiabatic asymmetric directional coupler, attempt 1 (parametric tier).

Top arm: straight w0.304 -> taper to 0.46 -> s-bend down -> coupling taper
0.488 -> 0.320 -> s-bend up -> exit straight. Bottom arm mirrors with opposite
width sense (0.30 -> 0.20, coupling 0.20 -> 0.29). All from calibrated measurements.
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def taper_at(c, x, y, length, w1, w2):
    t = c << gf.components.taper(length=length, width1=w1, width2=w2, layer=LAYER)
    t.move((x, y))
    return t


def sbend_at(c, x, y, size_x, size_y, w):
    b = c << gf.components.bend_s(size=(size_x, size_y), cross_section=xs(w))
    b.move((x, y))
    return b


def straight_at(c, x, y, length, w):
    s = c << gf.components.straight(length=length, cross_section=xs(w))
    s.move((x, y))
    return s


@gf.cell
def adc_v1() -> gf.Component:
    c = gf.Component()

    # --- top arm ---
    straight_at(c, 0.0, 1.735, 14.0, 0.304)
    taper_at(c, 14.0, 1.735, 5.0, 0.304, 0.460)
    sbend_at(c, 19.0, 1.735, 12.5, -1.510, 0.470)
    taper_at(c, 31.5, 0.225, 55.5, 0.488, 0.320)
    sbend_at(c, 87.0, 0.222, 14.5, 1.612, 0.340)
    straight_at(c, 101.5, 1.834, 18.5, 0.306)

    # --- bottom arm ---
    straight_at(c, 0.0, -1.710, 5.0, 0.300)
    taper_at(c, 5.0, -1.710, 14.0, 0.300, 0.200)
    sbend_at(c, 19.0, -1.712, 12.5, 1.477, 0.204)
    taper_at(c, 31.5, -0.235, 55.5, 0.204, 0.290)
    sbend_at(c, 87.0, -0.237, 14.5, -1.595, 0.310)
    straight_at(c, 101.5, -1.832, 18.5, 0.300)

    return c


if __name__ == "__main__":
    component = adc_v1()
    out = Path(__file__).parent / "attempt1.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
