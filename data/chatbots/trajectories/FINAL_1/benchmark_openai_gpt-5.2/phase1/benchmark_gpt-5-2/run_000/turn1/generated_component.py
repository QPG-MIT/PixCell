import gdsfactory as gf


@gf.cell
def trident_splitter(
    length_total: float = 40.0,
    height_total: float = 1.7,
    layer: tuple[int, int] = (1, 0),
):
    """
    Recreates the shown geometry using only parametric primitives + connections.
    No raw polygons.

    Geometry interpretation (from the PNG):
    - Three inputs on the left (top/mid/bot).
    - Top and bottom continue to the right and smoothly diverge (S-bends).
    - Middle is a thicker straight that stops before the split region.
    - Target footprint ~ (40 um x 1.7 um).
    """
    c = gf.Component()

    # ---- Cross-sections (widths chosen to fit in 1.7um total height) ----
    xs_arm = gf.cross_section.strip(width=0.40, layer=layer)   # top/bottom arms
    xs_mid = gf.cross_section.strip(width=0.60, layer=layer)   # center guide

    # ---- Layout parameters (chosen to match the picture + footprint) ----
    taper_len = 4.0
    straight_before_split = 18.0
    s_dx = 10.0
    out_len = length_total - (taper_len + straight_before_split + s_dx)  # -> 8.0

    # Left-side centerline positions (three guides)
    y0 = 0.35  # top at +0.35, mid at 0, bottom at -0.35

    # Additional offset produced by the S-bends to reach final separation
    # (kept small to stay within 1.7um bbox)
    dy = 0.25

    # ---- Building blocks ----
    taper_arm = gf.components.taper(
        length=taper_len, width1=0.25, width2=xs_arm.width, layer=layer
    )
    taper_mid = gf.components.taper(
        length=taper_len, width1=0.25, width2=xs_mid.width, layer=layer
    )

    st_arm = gf.components.straight(length=straight_before_split, cross_section=xs_arm)
    st_mid = gf.components.straight(length=straight_before_split, cross_section=xs_mid)

    sb_top = gf.components.bend_s(size=(s_dx, +dy), cross_section=xs_arm)
    sb_bot = gf.components.bend_s(size=(s_dx, -dy), cross_section=xs_arm)

    st_out = gf.components.straight(length=out_len, cross_section=xs_arm)

    # ---- TOP arm chain ----
    top_t = c << taper_arm
    top_t.move((0, y0))
    top_s = c << st_arm
    top_s.connect("o1", top_t.ports["o2"])
    top_b = c << sb_top
    top_b.connect("o1", top_s.ports["o2"])
    top_o = c << st_out
    top_o.connect("o1", top_b.ports["o2"])

    # ---- BOTTOM arm chain ----
    bot_t = c << taper_arm
    bot_t.move((0, -y0))
    bot_s = c << st_arm
    bot_s.connect("o1", bot_t.ports["o2"])
    bot_b = c << sb_bot
    bot_b.connect("o1", bot_s.ports["o2"])
    bot_o = c << st_out
    bot_o.connect("o1", bot_b.ports["o2"])

    # ---- MIDDLE (thicker) guide that stops before the split ----
    mid_t = c << taper_mid
    mid_t.move((0, 0))
    mid_s = c << st_mid
    mid_s.connect("o1", mid_t.ports["o2"])
    # (No continuation after this straight: it terminates like in the PNG.)

    # ---- External ports (left inputs + right outputs) ----
    c.add_port("in_top", port=top_t.ports["o1"])
    c.add_port("in_mid", port=mid_t.ports["o1"])
    c.add_port("in_bot", port=bot_t.ports["o1"])
    c.add_port("out_top", port=top_o.ports["o2"])
    c.add_port("out_bot", port=bot_o.ports["o2"])

    # Optional: ensure footprint is within the requested bounds (approx).
    # bbox = c.bbox
    # print("bbox (um):", (bbox[1][0] - bbox[0][0], bbox[1][1] - bbox[0][1]))

    return c


if __name__ == "__main__":
    c = trident_splitter()
    c.show()
    c.write_gds("trident_splitter.gds")