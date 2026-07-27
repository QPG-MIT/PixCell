import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    length_s = 30
    length_center = 120 - 2 * length_s
    port_y = 1.75

    # Left top S-bend
    left_top = gf.components.bend_s(size=(length_s, -port_y), cross_section=xs)
    ref_lt = c << left_top
    ref_lt.move((0, port_y))

    # Left bottom S-bend
    left_bottom = gf.components.bend_s(size=(length_s, port_y), cross_section=xs)
    ref_lb = c << left_bottom
    ref_lb.move((0, -port_y))

    # Center straight
    center = gf.components.straight(length=length_center, cross_section=xs)
    ref_c = c << center
    ref_c.connect("o1", ref_lt.ports["o2"])

    # Right top S-bend
    right_top = gf.components.bend_s(size=(length_s, port_y), cross_section=xs)
    ref_rt = c << right_top
    ref_rt.connect("o2", ref_c.ports["o2"])

    # Right bottom S-bend
    right_bottom = gf.components.bend_s(size=(length_s, -port_y), cross_section=xs)
    ref_rb = c << right_bottom
    ref_rb.connect("o2", ref_c.ports["o2"])

    # Optional: Expose ports (though not necessary for pure geometry recreation)
    c.add_port("left_bottom", port=ref_lb.ports["o1"])
    c.add_port("left_top", port=ref_lt.ports["o1"])
    c.add_port("right_bottom", port=ref_rb.ports["o1"])
    c.add_port("right_top", port=ref_rt.ports["o1"])

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")