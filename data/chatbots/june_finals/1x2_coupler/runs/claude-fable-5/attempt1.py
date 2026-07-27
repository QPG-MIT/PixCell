"""Trident 1x2 adiabatic splitter — recreated from target image measurements.

Geometry (um), measured from component.png via calibration (40.4 px/um x, 307.06 px/um y):
- center input: straight w=0.270 for x in [0, 3.04], then taper 0.270 -> 0.04 ending x=25.07
- arms: tip w=0.072 at x=3.04, centerlines +0.281 / -0.259, linear taper to w=0.246 at x=26.0
- s-bends: x 26.0 -> 36.0, dy +0.449 (top) / -0.469 (bottom)
- outputs: straight to x=40.0 at c=+0.730 / -0.728
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)


@gf.cell
def trident_splitter() -> gf.Component:
    c = gf.Component()

    # --- center input: straight + taper to a point ---
    xs_in = gf.cross_section.cross_section(width=0.270, layer=LAYER)
    stub = c << gf.components.straight(length=3.04, cross_section=xs_in)
    stub.move((0, 0.016))
    center_taper = c << gf.components.taper(length=22.03, width1=0.270, width2=0.04, layer=LAYER)
    center_taper.connect("o1", stub.ports["o2"])

    # --- top arm: taper -> s-bend up -> output straight ---
    xs_arm = gf.cross_section.cross_section(width=0.246, layer=LAYER)
    top_taper = c << gf.components.taper(length=22.96, width1=0.072, width2=0.246, layer=LAYER)
    top_taper.move((3.04, 0.281))
    top_sbend = c << gf.components.bend_s(size=(10.0, 0.449), cross_section=xs_arm)
    top_sbend.connect("o1", top_taper.ports["o2"])
    top_out = c << gf.components.straight(length=4.0, cross_section=xs_arm)
    top_out.connect("o1", top_sbend.ports["o2"])

    # --- bottom arm: mirror with measured offsets ---
    bot_taper = c << gf.components.taper(length=22.96, width1=0.072, width2=0.246, layer=LAYER)
    bot_taper.move((3.04, -0.259))
    bot_sbend = c << gf.components.bend_s(size=(10.0, -0.469), cross_section=xs_arm)
    bot_sbend.connect("o1", bot_taper.ports["o2"])
    bot_out = c << gf.components.straight(length=4.0, cross_section=xs_arm)
    bot_out.connect("o1", bot_sbend.ports["o2"])

    return c


if __name__ == "__main__":
    component = trident_splitter()
    out = Path(__file__).parent / "attempt1.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
