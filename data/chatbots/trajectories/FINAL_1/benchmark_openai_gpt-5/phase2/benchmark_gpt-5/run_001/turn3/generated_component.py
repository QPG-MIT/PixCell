import gdsfactory as gf


@gf.cell
def fork_funnel_v3():
    c = gf.Component("fork_funnel_v3")

    # footprint
    L_total = 40.0
    H_total = 1.7

    # widths (µm)
    w_tip = 0.12            # thin rails at the far left
    w_rail = 0.90           # wide rails on the right
    w_center_base = 0.50    # center wedge base (left)
    w_center_tip = 0.06     # center wedge tip (right)

    # lengths (µm)
    L_taper = 26.0          # left taper length
    dx_s = 6.0              # S-bend x-span
    L_right = L_total - L_taper - dx_s  # keep total ~40 µm (≈8 µm)

    # vertical placement
    clearance = 0.04                           # gap between center wedge and side rails (left)
    y_left = w_center_base/2 + w_tip/2 + clearance   # ≈ 0.35–0.36 µm
    y_right = H_total/2 - w_rail/2                    # sets total height to 1.7 µm (≈0.40 µm)
    dy = y_right - y_left                              # small fanout in the S-bend

    xs_rail = gf.cross_section.cross_section(width=w_rail, layer=(1, 0))

    # Top branch
    t_top = c << gf.components.taper(length=L_taper, width1=w_rail, width2=w_tip, layer=(1, 0))
    t_top.rotate(180)
    t_top.movey(+y_left)

    s_top = c << gf.components.bend_s(size=(dx_s, +dy), cross_section=xs_rail)
    s_top.connect("o1", t_top.ports["o1"])

    r_top = c << gf.components.straight(length=L_right, cross_section=xs_rail)
    r_top.connect("o1", s_top.ports["o2"])

    # Bottom branch
    t_bot = c << gf.components.taper(length=L_taper, width1=w_rail, width2=w_tip, layer=(1, 0))
    t_bot.rotate(180)
    t_bot.movey(-y_left)

    s_bot = c << gf.components.bend_s(size=(dx_s, -dy), cross_section=xs_rail)
    s_bot.connect("o1", t_bot.ports["o1"])

    r_bot = c << gf.components.straight(length=L_right, cross_section=xs_rail)
    r_bot.connect("o1", s_bot.ports["o2"])

    # Center wedge: stop before the S-bends start to avoid scallops
    center_len = L_taper - 0.6  # ~0.6 µm buffer before S-bends
    _center = c << gf.components.taper(
        length=center_len, width1=w_center_base, width2=w_center_tip, layer=(1, 0)
    )

    return c


if __name__ == "__main__":
    comp = fork_funnel_v3()
    comp.write_gds("fork_funnel_v3.gds")