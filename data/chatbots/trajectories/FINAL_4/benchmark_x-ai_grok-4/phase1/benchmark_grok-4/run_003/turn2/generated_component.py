import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()

    width = 0.5
    gap = 0.2
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    length = 18.0
    height = 3.0
    center_sep = (height - width) / 2  # 1.25
    center_close = (width + gap) / 2  # 0.35
    delta = center_sep - center_close  # 0.9
    half_length = length / 2  # 9.0

    # Base bend_s for positive offset
    b = gf.components.bend_s(size=(half_length, delta), cross_section=xs)

    # Top waveguide: first down (negative dy), then up (positive dy)
    first_top = c << b
    first_top.mirror(p1=(0, 0), p2=(1, 0))  # flip to negative dy
    first_top.move((0, center_sep))
    second_top = c << b
    second_top.connect("o1", first_top.ports["o2"])

    # Bottom waveguide: first up (positive dy), then down (negative dy)
    first_bottom = c << b
    first_bottom.move((0, -center_sep))
    second_bottom = c << b
    second_bottom.mirror(p1=(0, 0), p2=(1, 0))  # flip to negative dy
    second_bottom.connect("o1", first_bottom.ports["o2"])

    # Add ports
    c.add_port("o1", port=first_top.ports["o1"])
    c.add_port("o2", port=second_top.ports["o2"])
    c.add_port("o3", port=first_bottom.ports["o1"])
    c.add_port("o4", port=second_bottom.ports["o2"])

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")