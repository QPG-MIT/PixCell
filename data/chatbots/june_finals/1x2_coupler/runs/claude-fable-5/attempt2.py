"""Trident 1x2 splitter, attempt 2.

Fixes vs attempt 1 (IoU 0.9545):
- center taper tip widened to the measured 0.075 um (was 0.04)
- arm tapers tilted to follow measured centerline drift (top +0.2817 -> +0.2780,
  bottom -0.2620 -> -0.2510) using path + linear width transition
- s-bend / output widths set per-arm from measurements
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


@gf.cell
def trident_splitter_v2() -> gf.Component:
    c = gf.Component()

    # --- center input: straight + taper ---
    stub = c << gf.components.straight(length=3.04, cross_section=xs(0.270))
    stub.move((0, 0.016))
    center_taper = c << gf.components.taper(length=22.06, width1=0.270, width2=0.076, layer=LAYER)
    center_taper.connect("o1", stub.ports["o2"])

    # --- arm tapers: tilted, linear width transition ---
    trans = gf.path.transition(xs(0.066), xs(0.248), width_type="linear")

    top_path = gf.Path([(3.04, 0.2817), (26.2, 0.2780)])
    c << gf.path.extrude_transition(top_path, trans)

    bot_path = gf.Path([(3.04, -0.2620), (26.2, -0.2510)])
    c << gf.path.extrude_transition(bot_path, trans)

    # --- s-bends ---
    top_sbend = c << gf.components.bend_s(size=(9.9, 0.4515), cross_section=xs(0.248))
    top_sbend.move((26.2, 0.2780))
    bot_sbend = c << gf.components.bend_s(size=(9.9, -0.4769), cross_section=xs(0.248))
    bot_sbend.move((26.2, -0.2510))

    # --- output straights ---
    top_out = c << gf.components.straight(length=3.9, cross_section=xs(0.244))
    top_out.move((36.1, 0.7295))
    bot_out = c << gf.components.straight(length=3.9, cross_section=xs(0.240))
    bot_out.move((36.1, -0.7279))

    return c


if __name__ == "__main__":
    component = trident_splitter_v2()
    out = Path(__file__).parent / "attempt2.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
