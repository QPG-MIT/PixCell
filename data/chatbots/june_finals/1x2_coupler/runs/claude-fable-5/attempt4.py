"""Trident 1x2 splitter, attempt 4.

Fixes vs attempt 3 (IoU 0.9826):
- center taper closes to a point (0.076 -> 0.044 over the last 0.15 um)
- s-bends extruded with measured width variation (0.246 -> 0.250 -> 0.244)
  by splitting each bend path at its midpoint
- input stub trimmed to measured w=0.272, c=+0.015
"""

from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

TOP_BEND = [
    (25.9, 0.2806), (26.238, 0.2817), (26.733, 0.2866), (27.228, 0.2931),
    (27.723, 0.3078), (28.218, 0.3257), (28.713, 0.3501), (29.208, 0.3778),
    (29.703, 0.4103), (30.198, 0.4478), (30.693, 0.4885), (31.188, 0.5292),
    (31.683, 0.5699), (32.178, 0.609), (32.673, 0.6416), (33.168, 0.6693),
    (33.663, 0.6904), (34.158, 0.7051), (34.653, 0.7165), (35.149, 0.723),
    (35.644, 0.7262), (36.139, 0.7295), (36.7, 0.7295),
]

BOT_BEND = [
    (25.9, -0.2512), (26.238, -0.2524), (26.733, -0.2557), (27.228, -0.2638),
    (27.723, -0.2768), (28.218, -0.2931), (28.713, -0.3175), (29.208, -0.3468),
    (29.703, -0.3827), (30.198, -0.4217), (30.693, -0.4641), (31.188, -0.508),
    (31.683, -0.5488), (32.178, -0.5878), (32.673, -0.622), (33.168, -0.6497),
    (33.663, -0.6725), (34.158, -0.692), (34.653, -0.7051), (35.149, -0.7148),
    (35.644, -0.723), (36.139, -0.7262), (36.7, -0.7279),
]

MID = 11  # waypoint index near the bend midpoint (x ~ 31.2)


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def add_bend(c: gf.Component, pts) -> None:
    rise = gf.path.transition(xs(0.246), xs(0.250), width_type="linear")
    fall = gf.path.transition(xs(0.250), xs(0.244), width_type="linear")
    c << gf.path.extrude_transition(gf.Path(pts[: MID + 1]), rise)
    c << gf.path.extrude_transition(gf.Path(pts[MID:]), fall)


@gf.cell
def trident_splitter_v4() -> gf.Component:
    c = gf.Component()

    # --- center input: straight + taper + tip closure ---
    stub = c << gf.components.straight(length=3.04, cross_section=xs(0.272))
    stub.move((0, 0.015))
    body = c << gf.components.taper(length=21.91, width1=0.272, width2=0.076, layer=LAYER)
    body.connect("o1", stub.ports["o2"])
    tip = c << gf.components.taper(length=0.15, width1=0.076, width2=0.044, layer=LAYER)
    tip.connect("o1", body.ports["o2"])

    # --- arm tapers: tilted, linear width transition ---
    trans = gf.path.transition(xs(0.066), xs(0.246), width_type="linear")
    c << gf.path.extrude_transition(gf.Path([(3.04, 0.2817), (25.9, 0.2806)]), trans)
    c << gf.path.extrude_transition(gf.Path([(3.04, -0.2620), (25.9, -0.2512)]), trans)

    # --- s-bends with measured width variation ---
    add_bend(c, TOP_BEND)
    add_bend(c, BOT_BEND)

    # --- output straights ---
    top_out = c << gf.components.straight(length=3.3, cross_section=xs(0.244))
    top_out.move((36.7, 0.7295))
    bot_out = c << gf.components.straight(length=3.3, cross_section=xs(0.240))
    bot_out.move((36.7, -0.7282))

    return c


if __name__ == "__main__":
    component = trident_splitter_v4()
    out = Path(__file__).parent / "attempt4.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
