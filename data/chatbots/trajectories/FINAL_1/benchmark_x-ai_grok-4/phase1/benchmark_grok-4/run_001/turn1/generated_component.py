import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    # Cross sections
    left_width = 0.2
    arm_width = 0.3
    min_width = 0.002
    xs_left = gf.cross_section.cross_section(width=left_width, layer=layer)
    xs_arm = gf.cross_section.cross_section(width=arm_width, layer=layer)

    # Parameters (tuned approximately to footprint [40.0, 1.7])
    left_length = 18.0
    taper_left_length = 8.0
    gap = 0
    initial_angle = 20  # degrees
    taper_split_length = 2.0
    bend_radius = 8.0
    taper_end_length = 9.0

    # Left part: straight + taper to point
    s_left = c << gf.components.straight(length=left_length, cross_section=xs_left)
    t_left = c << gf.components.taper(length=taper_left_length, width1=left_width, width2=min_width)
    t_left.connect("o1", s_left.ports["o2"])

    # Right tip position
    tip_x = left_length + taper_left_length + gap
    tip_y = 0

    # Upper arm
    ut = c << gf.components.taper(length=taper_split_length, width1=min_width, width2=arm_width)
    ut.rotate(initial_angle)
    ut.move(origin=ut.ports["o1"], destination=(tip_x, tip_y))

    ub = c << gf.components.bend_euler(radius=bend_radius, angle=-initial_angle, p=0.5, cross_section=xs_arm)
    ub.connect("o1", ut.ports["o2"])

    ute = c << gf.components.taper(length=taper_end_length, width1=arm_width, width2=min_width)
    ute.connect("o1", ub.ports["o2"])

    # Lower arm
    lt = c << gf.components.taper(length=taper_split_length, width1=min_width, width2=arm_width)
    lt.rotate(-initial_angle)
    lt.move(origin=lt.ports["o1"], destination=(tip_x, tip_y))

    lb = c << gf.components.bend_euler(radius=bend_radius, angle=initial_angle, p=0.5, cross_section=xs_arm)
    lb.connect("o1", lt.ports["o2"])

    lte = c << gf.components.taper(length=taper_end_length, width1=arm_width, width2=min_width)
    lte.connect("o1", lb.ports["o2"])

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")