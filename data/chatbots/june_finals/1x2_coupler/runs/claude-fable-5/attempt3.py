"""Trident 1x2 splitter, attempt 3.

Fix vs attempt 2 (IoU 0.9665): bend_s beziers replaced with paths through the
measured s-bend centerlines (gf.Path waypoints, constant-width extrusion).
Each arm: tilted linear-width taper -> measured centerline path -> output straight.
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


def xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


@gf.cell
def trident_splitter_v3() -> gf.Component:
    c = gf.Component()

    # --- center input: straight + taper ---
    stub = c << gf.components.straight(length=3.04, cross_section=xs(0.270))
    stub.move((0, 0.016))
    center_taper = c << gf.components.taper(length=22.06, width1=0.270, width2=0.076, layer=LAYER)
    center_taper.connect("o1", stub.ports["o2"])

    # --- arm tapers: tilted, linear width transition, ending where the bends pick up ---
    trans = gf.path.transition(xs(0.066), xs(0.248), width_type="linear")
    c << gf.path.extrude_transition(gf.Path([(3.04, 0.2817), (25.9, 0.2806)]), trans)
    c << gf.path.extrude_transition(gf.Path([(3.04, -0.2620), (25.9, -0.2512)]), trans)

    # --- s-bends: measured centerline waypoints, constant width ---
    c << gf.path.extrude(gf.Path(TOP_BEND), cross_section=xs(0.248))
    c << gf.path.extrude(gf.Path(BOT_BEND), cross_section=xs(0.248))

    # --- output straights ---
    top_out = c << gf.components.straight(length=3.3, cross_section=xs(0.244))
    top_out.move((36.7, 0.7295))
    bot_out = c << gf.components.straight(length=3.3, cross_section=xs(0.240))
    bot_out.move((36.7, -0.7279))

    return c


if __name__ == "__main__":
    component = trident_splitter_v3()
    out = Path(__file__).parent / "attempt3.gds"
    component.write_gds(str(out))
    print(f"wrote {out}")
