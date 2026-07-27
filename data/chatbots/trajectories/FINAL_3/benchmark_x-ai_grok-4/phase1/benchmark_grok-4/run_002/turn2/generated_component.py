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
    dy_shift = y_end - y_middle

    c = gf.Component()

    mid = c << gf.components.coupler_straight(
        length=length_middle, gap=gap, cross_section=xs
    )

    # Upper left bend
    blu = c << gf.components.bend_s(
        size=(dx_bend, dy_shift), cross_section=xs
    )
    blu.connect("o2", mid.ports["o2"])

    # Lower left bend
    bll = c << gf.components.bend_s(
        size=(dx_bend, -dy_shift), cross_section=xs
    )
    bll.connect("o2", mid.ports["o1"])

    # Upper right bend
    bru = c << gf.components.bend_s(
        size=(dx_bend, dy_shift), cross_section=xs
    )
    bru.connect("o1", mid.ports["o4"])

    # Lower right bend
    brl = c << gf.components.bend_s(
        size=(dx_bend, -dy_shift), cross_section=xs
    )
    brl.connect("o1", mid.ports["o3"])

    # Add ports
    c.add_port("o1", port=blu.ports["o1"])
    c.add_port("o2", port=bll.ports["o1"])
    c.add_port("o3", port=bru.ports["o2"])
    c.add_port("o4", port=brl.ports["o2"])

    return c

# Create and save
device = symmetric_coupler()
device.write_gds("device.gds")