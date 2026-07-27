import gdsfactory as gf

@gf.cell
def symmetric_coupler():
    width = 0.5
    gap = 0.2
    length_middle = 40
    dx_bend = 40
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    y_middle = (width + gap) / 2
    y_end = 1.75
    dy_shift = y_end + y_middle
    h = y_end
    total_length = 120
    total_dy = 2 * h

    c = gf.Component()

    # Path 1: bottom left to top right
    bend1 = c << gf.components.bend_s(
        size=(total_length, total_dy), cross_section=xs
    )
    bend1.move((0, -h))

    # Path 2: top left to bottom right
    bend2 = c << gf.components.bend_s(
        size=(total_length, -total_dy), cross_section=xs
    )
    bend2.move((0, h))

    # Add ports
    c.add_port("o1", port=bend1.ports["o1"])
    c.add_port("o2", port=bend2.ports["o1"])
    c.add_port("o3", port=bend2.ports["o2"])
    c.add_port("o4", port=bend1.ports["o2"])

    return c

# Create and save
device = symmetric_coupler()
device.write_gds("device.gds")