import gdsfactory as gf

@gf.cell
def fork_splitter_v3():
    c = gf.Component("fork_splitter_v3")

    # Footprint
    L_total = 40.0
    L_tail = 10.0
    x_knee = L_total - L_tail  # where the bend levels to a straight tail

    # Widths / offsets
    w_start = 0.01
    w_end = 0.50
    y_out = 0.60                      # final centerline offset (=> total height = 1.7 µm)
    g0 = 0.03                         # small separation at the very left

    # Cross‑sections and taper
    xs0 = gf.cross_section.cross_section(width=w_start, layer=(1, 0))
    xs1 = gf.cross_section.cross_section(width=w_end, layer=(1, 0))
    trans = gf.path.transition(xs0, xs1, width_type="sine")

    # Where the flare finishes; after this the arms keep constant width
    L_trans = 20.0
    y_trans = 0.18
    R = 16.0                          # smoothness of the bends

    # ---- TOP arm ----
    p_top_taper = gf.path.smooth(
        points=[(0, +g0/2), (8, 0.02), (14, 0.09), (L_trans, +y_trans)],
        radius=R,
    )
    top_taper = gf.path.extrude_transition(p_top_taper, trans)

    p_top_const = (
        gf.path.smooth(points=[(0, 0), (x_knee - L_trans, +y_out - y_trans)], radius=R)
        + gf.path.straight(length=L_tail)
    )
    top_const = gf.path.extrude(p_top_const, cross_section=xs1)

    rt1 = c << top_taper
    rt2 = c << top_const
    rt2.connect("o1", rt1.ports["o2"])

    # ---- BOTTOM arm (mirror of top) ----
    p_bot_taper = gf.path.smooth(
        points=[(0, -g0/2), (8, -0.02), (14, -0.09), (L_trans, -y_trans)],
        radius=R,
    )
    bot_taper = gf.path.extrude_transition(p_bot_taper, trans)

    p_bot_const = (
        gf.path.smooth(points=[(0, 0), (x_knee - L_trans, -(y_out - y_trans))], radius=R)
        + gf.path.straight(length=L_tail)
    )
    bot_const = gf.path.extrude(p_bot_const, cross_section=xs1)

    rb1 = c << bot_taper
    rb2 = c << bot_const
    rb2.connect("o1", rb1.ports["o2"])

    # ---- Center tine (short stub that stops before the split) ----
    L_tine = L_trans + 2.0            # ends a little after the arm flares finish
    p_mid = gf.path.straight(length=L_tine)
    mid = gf.path.extrude_transition(p_mid, trans)
    c << mid

    # Output ports
    c.add_port("o_top", port=rt2.ports["o2"])
    c.add_port("o_bot", port=rb2.ports["o2"])

    # Total vertical span remains 2*(y_out + w_end/2) = 1.7 µm
    return c

if __name__ == "__main__":
    c = fork_splitter_v3()
    c.write_gds("fork_splitter_v3.gds")
    # c.show()