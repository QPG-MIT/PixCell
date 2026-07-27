import gdsfactory as gf


@gf.cell
def fork_with_triple_tapers_v3():
    c = gf.Component()

    # Footprint target
    W = 40.0
    H = 1.7  # not used directly

    # Left three tapers
    L_taper = 22.0
    w_mid1 = 0.52
    w_outer1 = 0.36
    w_mid2 = 0.16
    w_outer2 = 0.08

    y_mid = 0.0
    y_outer = 0.58  # centers of the top/bottom tapers

    t_mid = c << gf.components.taper(length=L_taper, width1=w_mid1, width2=w_mid2, cross_section="strip")
    t_top = c << gf.components.taper(length=L_taper, width1=w_outer1, width2=w_outer2, cross_section="strip")
    t_bot = c << gf.components.taper(length=L_taper, width1=w_outer1, width2=w_outer2, cross_section="strip")

    t_mid.move((0, y_mid))
    t_top.move((0, +y_outer))
    t_bot.move((0, -y_outer))

    # Small gap between the tapers and the right rails
    gap_x = 0.12

    # Right rails: flare outward from near the center to the final offset
    xs_wide = gf.cross_section.strip(width=0.60, layer=(1, 0))
    s_dx = 12.0
    y_in = 0.30
    dy = 0.25  # so y_out = 0.55, outer edges land close to ±0.85 with width=0.60

    s_top = c << gf.components.bend_s(size=(s_dx, +dy), cross_section=xs_wide)
    s_bot = c << gf.components.bend_s(size=(s_dx, -dy), cross_section=xs_wide)

    # Place S-bends so their inputs are just to the right of the tapers
    p = s_top.ports["o1"]
    s_top.move(((L_taper + gap_x) - p.center[0], y_in - p.center[1]))
    p = s_bot.ports["o1"]
    s_bot.move(((L_taper + gap_x) - p.center[0], -y_in - p.center[1]))

    # Straight rails to the right edge
    L_right = W - (L_taper + gap_x + s_dx)
    st_top = c << gf.components.straight(length=L_right, cross_section=xs_wide)
    st_bot = c << gf.components.straight(length=L_right, cross_section=xs_wide)
    st_top.connect("o1", s_top.ports["o2"])
    st_bot.connect("o1", s_bot.ports["o2"])

    return c


if __name__ == "__main__":
    comp = fork_with_triple_tapers_v3()
    comp.write_gds("fork_with_triple_tapers_v3.gds")
    print("Wrote GDS: fork_with_triple_tapers_v3.gds")