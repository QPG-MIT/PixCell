# Generates and saves the GDS file for the forked/tapered geometry
# Footprint approx: 40.0 µm (x) by 1.7 µm (y)

import gdsfactory as gf


@gf.cell
def fork_with_triple_tapers():
    c = gf.Component()

    W = 40.0  # total device length
    H = 1.7

    # Geometry choices matching the image
    L_taper = 22.0
    gap_x = 0.30
    s_dx = 8.0
    L_right = W - (L_taper + gap_x + s_dx)

    # Wide rails on the right
    xs_wide = gf.cross_section.strip(width=0.60, layer=(1, 0))

    # Three left tapers
    t_mid = c << gf.components.taper(length=L_taper, width1=0.70, width2=0.12, cross_section="strip")
    t_top = c << gf.components.taper(length=L_taper, width1=0.35, width2=0.06, cross_section="strip")
    t_bot = c << gf.components.taper(length=L_taper, width1=0.35, width2=0.06, cross_section="strip")

    # Arrange the three prongs
    t_mid.move((0, 0.0))
    t_top.move((0, +0.22))
    t_bot.move((0, -0.22))

    # Two thick rails curving inward
    y_start = 0.55
    s_top = c << gf.components.bend_s(size=(s_dx, -0.20), cross_section=xs_wide)
    s_bot = c << gf.components.bend_s(size=(s_dx, +0.20), cross_section=xs_wide)

    # Place S-bends by aligning their input-port centers to coordinates
    p = s_top.ports["o1"]
    s_top.move(((L_taper + gap_x) - p.center[0], y_start - p.center[1]))
    p = s_bot.ports["o1"]
    s_bot.move(((L_taper + gap_x) - p.center[0], -y_start - p.center[1]))

    # Straight rails to reach the right edge
    st_top = c << gf.components.straight(length=L_right, cross_section=xs_wide)
    st_bot = c << gf.components.straight(length=L_right, cross_section=xs_wide)
    st_top.connect("o1", s_top.ports["o2"])
    st_bot.connect("o1", s_bot.ports["o2"])

    return c


if __name__ == "__main__":
    comp = fork_with_triple_tapers()
    # Save the GDS file
    comp.write_gds("fork_with_triple_tapers.gds")
    print("Wrote GDS: fork_with_triple_tapers.gds")