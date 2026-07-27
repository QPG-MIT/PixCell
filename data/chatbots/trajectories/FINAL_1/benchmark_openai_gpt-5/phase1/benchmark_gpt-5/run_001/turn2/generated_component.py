import gdsfactory as gf


@gf.cell
def fork_funnel():
    c = gf.Component("fork_funnel_fix2")

    # Target footprint ≈ 40 µm x 1.7 µm
    w_tip = 0.12           # thin left tips (top/bottom rails)
    w_rail = 0.90          # wide rails to the right
    w_center_base = 0.50   # center wedge base (left)
    w_center_tip = 0.06    # center wedge tip (right)

    # Lengths (µm)
    L_taper = 26.0         # long tapers on the left
    dx_s = 6.0             # S-bend x-span
    L_right = 8.0          # right straight section
    # total ≈ 40 µm

    # Vertical placement for ~1.7 µm total height
    y_left = 0.25
    y_right = 0.85
    dy = y_right - y_left

    xs_rail = gf.cross_section.cross_section(width=w_rail, layer=(1, 0))

    # Top branch: taper (narrow on left), then s-bend fanout, then straight
    t_top = c << gf.components.taper(length=L_taper, width1=w_rail, width2=w_tip, layer=(1, 0))
    t_top.rotate(180)        # puts the narrow end on the left
    t_top.movey(y_left)

    s_top = c << gf.components.bend_s(size=(dx_s, dy), cross_section=xs_rail)
    # Connect to the wide end of the taper (port "o1" after rotation)
    s_top.connect("o1", t_top.ports["o1"])

    r_top = c << gf.components.straight(length=L_right, cross_section=xs_rail)
    r_top.connect("o1", s_top.ports["o2"])

    # Bottom branch (mirrored vertically)
    t_bot = c << gf.components.taper(length=L_taper, width1=w_rail, width2=w_tip, layer=(1, 0))
    t_bot.rotate(180)
    t_bot.movey(-y_left)

    s_bot = c << gf.components.bend_s(size=(dx_s, -dy), cross_section=xs_rail)
    s_bot.connect("o1", t_bot.ports["o1"])

    r_bot = c << gf.components.straight(length=L_right, cross_section=xs_rail)
    r_bot.connect("o1", s_bot.ports["o2"])

    # Center wedge intruding from the left
    center_len = 31.0
    _center = c << gf.components.taper(
        length=center_len, width1=w_center_base, width2=w_center_tip, layer=(1, 0)
    )
    # centered at y=0 already

    return c


if __name__ == "__main__":
    comp = fork_funnel()
    comp.write_gds("fork_funnel.gds")