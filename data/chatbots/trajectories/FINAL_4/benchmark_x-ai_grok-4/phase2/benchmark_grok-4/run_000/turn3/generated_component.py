import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    sep_ends = 2.5
    dy = sep_ends

    # Path1: bottom left to top right
    path1 = gf.components.bend_s(size=(18, dy), cross_section=xs)
    p1_ref = c << path1
    p1_ref.move((0, 0.25))

    # Path2: top left to bottom right
    path2 = gf.components.bend_s(size=(18, -dy), cross_section=xs)
    p2_ref = c << path2
    p2_ref.move((0, sep_ends + 0.5 - 0.25))  # 2.5 + 0.5 / 2 * 2 = 2.75

    # Expose ports
    c.add_port("o1", port=p1_ref.ports["o1"])
    c.add_port("o2", port=p2_ref.ports["o1"])
    c.add_port("o3", port=p2_ref.ports["o2"])
    c.add_port("o4", port=p1_ref.ports["o2"])

    # Shift to start at y=0
    c.move((0, -c.ymin))

    return c

dev = device()
dev.write_gds("device.gds")