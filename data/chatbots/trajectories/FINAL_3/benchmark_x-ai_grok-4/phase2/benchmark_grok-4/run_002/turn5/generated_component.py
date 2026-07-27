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

    c = gf.Component()

    # Path 1: bottom left to top right
    bend1 = c << gf.components.bend_s(
        size=(dx_bend, dy_shift), cross_section=xs
    )
    bend1.move((0, -h))

    # Path 2: top left to bottom right
    bend2 = c << gf.components.bend_s(
        size=(dx_bend, -dy_shift), cross_section=xs
    )
    bend2.move((0, h))

    # Middle coupler
    middle = c << gf.components.coupler_straight(
        length=length_middle, gap=gap, cross_section=xs
    )
    middle.move((dx_bend, 0))

    # Right bends
    bend3 = c << gf.components.bend_s(
        size=(dx_bend, dy_shift), cross_section=xs
    )
    bend3.move((dx_bend + length_middle, -y_middle))

    bend4 = c << gf.components.bend_s(
        size=(dx_bend, -dy_shift), cross_section=xs
    )
    bend4.move((dx_bend + length_middle, y_middle))

    # Add ports
    c.add_port("o1", port=bend1.ports["o1"])
    c.add_port("o2", port=bend2.ports["o1"])
    c.add_port("o3", port=bend4.ports["o2"])
    c.add_port("o4", port=bend3.ports["o2"])

    return c

# Create and save
device = symmetric_coupler()
device.write_gds("device.gds")