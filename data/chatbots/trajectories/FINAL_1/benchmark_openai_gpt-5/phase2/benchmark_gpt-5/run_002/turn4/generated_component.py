import gdsfactory as gf


@gf.cell
def fork_with_triple_tapers_v4():
    c = gf.Component()

    # Footprint target
    W = 40.0

    # Tapers: center longer than outers
    L_mid = 23.2
    L_outer = 21.2

    # Widths
    w_mid1, w_mid2 = 0.52, 0.16
    w_out1, w_out2 = 0.36, 0.08

    # Vertical positions of the 3 tapers
    y_mid = 0.0
    y_outer = 0.58

    # Build tapers
    t_mid = c << gf.components.taper(length=L_mid,  width1=w_mid1, width2=w_mid2,  cross_section="strip")
    t_top = c << gf.components.taper(length=L_outer, width1=w_out1, width2=w_out2, cross_section="strip")
    t_bot = c << gf.components.taper(length=L_outer, width1=w_out1, width2=w_out2, cross_section="strip")

    t_mid.move((0, y_mid))
    t_top.move((0, +y_outer))
    t_bot.move((0, -y_outer))

    # Small gap from center-taper tip to the right rails
    gap_mid = 0.06
    x_start = L_mid + gap_mid

    # Right rails: ensure a slit at the "throat"
    w_rail = 0.60
    xs_wide = gf.cross_section.strip(width=w_rail, layer=(1, 0))

    y_in = w_rail / 2 + 0.04  # > w/2 so rails don't merge (creates the white slit)
    y_out = 0.55              # final centerline position to keep edges near ±0.85
    dy = y_out - y_in
    s_dx = 14.0               # gentler flare than before

    s_top = c << gf.components.bend_s(size=(s_dx, +dy), cross_section=xs_wide)
    s_bot = c << gf.components.bend_s(size=(s_dx, -dy), cross_section=xs_wide)

    # Place S-bends so their inputs start just to the right of the center taper
    p = s_top.ports["o1"]
    s_top.move((x_start - p.center[0],  +y_in - p.center[1]))
    p = s_bot.ports["o1"]
    s_bot.move((x_start - p.center[0],  -y_in - p.center[1]))

    # Straight rails to the right edge
    L_right = W - (x_start + s_dx)
    st_top = c << gf.components.straight(length=L_right, cross_section=xs_wide)
    st_bot = c << gf.components.straight(length=L_right, cross_section=xs_wide)
    st_top.connect("o1", s_top.ports["o2"])
    st_bot.connect("o1", s_bot.ports["o2"])

    return c


if __name__ == "__main__":
    comp = fork_with_triple_tapers_v4()
    comp.write_gds("fork_with_triple_tapers_v4.gds")
    print("Wrote GDS: fork_with_triple_tapers_v4.gds")