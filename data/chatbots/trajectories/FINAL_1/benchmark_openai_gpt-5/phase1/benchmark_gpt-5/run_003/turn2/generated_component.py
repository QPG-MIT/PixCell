import gdsfactory as gf

@gf.cell
def fork_splitter_v2():
    c = gf.Component("fork_splitter_v2")

    # Footprint
    L_total = 40.0
    L_tail = 10.0                 # horizontal straight tail to the right
    x_knee = L_total - L_tail

    # Widths and offsets
    w_start = 0.01                # near-zero tip
    w_end = 0.50                  # constant output width
    y_out = 0.60                  # centerline offset at outputs
    g0 = 0.02                     # tiny initial centerline separation

    # Cross-sections and transition (gives the long triangular tips)
    xs0 = gf.cross_section.cross_section(width=w_start, layer=(1, 0))
    xs1 = gf.cross_section.cross_section(width=w_end, layer=(1, 0))
    trans = gf.path.transition(xs0, xs1, width_type="sine")

    # Curved flare that levels off, then a straight horizontal tail
    p_top = gf.path.smooth(
        points=[(0, +g0/2), (14, 0.05), (22, 0.22), (x_knee, +y_out)],
        radius=12.0,
    )
    p_top += gf.path.straight(length=L_tail)

    p_bot = gf.path.smooth(
        points=[(0, -g0/2), (14, -0.05), (22, -0.22), (x_knee, -y_out)],
        radius=12.0,
    )
    p_bot += gf.path.straight(length=L_tail)

    top = gf.path.extrude_transition(p_top, trans)
    bot = gf.path.extrude_transition(p_bot, trans)

    rt = c << top
    rb = c << bot

    c.add_port("o_top", port=rt.ports["o2"])
    c.add_port("o_bot", port=rb.ports["o2"])

    # Vertical span = 2*(y_out + w_end/2) = 1.7 µm
    return c

if __name__ == "__main__":
    c = fork_splitter_v2()
    c.write_gds("fork_splitter_v2.gds")
    # c.show()