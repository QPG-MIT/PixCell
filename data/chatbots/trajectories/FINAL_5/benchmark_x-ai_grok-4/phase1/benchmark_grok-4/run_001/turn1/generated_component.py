import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)
    width = 0.25
    gap = 0.2
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius_min=7.0)

    central_length = 8.0
    central = gf.components.coupler_straight(length=central_length, gap=gap, cross_section=xs)

    # Create slits for grating effect
    slit_width = 0.05
    period = 0.3
    n_slits = 26
    slits = gf.Component()
    margin = (central_length - (n_slits - 1) * period - slit_width) / 2
    first_x = -central_length / 2 + margin + slit_width / 2
    for i in range(n_slits):
        ref = slits << gf.components.rectangle(size=(slit_width, 0.8), layer=layer, centered=True)
        ref.move((first_x + i * period, 0))

    # Boolean to create grated central
    grated = gf.boolean(central, slits, operation="not", layer=layer)
    grated_ref = c << grated

    # Add ports manually (assuming standard positioning)
    center_bottom = -(gap / 2 + width / 2)
    center_top = (gap / 2 + width / 2)
    c.add_port(name="o1", center=(-central_length / 2, center_bottom), width=width, orientation=180, layer=layer)
    c.add_port(name="o2", center=(-central_length / 2, center_top), width=width, orientation=180, layer=layer)
    c.add_port(name="o3", center=(central_length / 2, center_bottom), width=width, orientation=0, layer=layer)
    c.add_port(name="o4", center=(central_length / 2, center_top), width=width, orientation=0, layer=layer)

    # Taper parameters
    taper_length = 1.0
    taper_width2 = 0.01

    # Left side small S-bends and tapers
    left_dx = 2.0
    left_dy = 0.1

    # Left top
    s_left_top = gf.components.bend_s(size=(left_dx, -left_dy), cross_section=xs)
    s_left_top_ref = c << s_left_top
    s_left_top_ref.connect("o1", c.ports["o2"])

    taper_left_top = gf.components.taper(length=taper_length, width1=width, width2=taper_width2, layer=layer)
    taper_left_top_ref = c << taper_left_top
    taper_left_top_ref.connect("o1", s_left_top_ref.ports["o2"])

    # Left bottom
    s_left_bottom = gf.components.bend_s(size=(left_dx, left_dy), cross_section=xs)
    s_left_bottom_ref = c << s_left_bottom
    s_left_bottom_ref.connect("o1", c.ports["o1"])

    taper_left_bottom = gf.components.taper(length=taper_length, width1=width, width2=taper_width2, layer=layer)
    taper_left_bottom_ref = c << taper_left_bottom
    taper_left_bottom_ref.connect("o1", s_left_bottom_ref.ports["o2"])

    # Right side large S-bends and tapers
    right_dx = 6.24
    right_dy = gap + width  # 0.45

    # Right top
    s_right_top = gf.components.bend_s(size=(right_dx, -right_dy), cross_section=xs)
    s_right_top_ref = c << s_right_top
    s_right_top_ref.connect("o1", c.ports["o4"])

    taper_right_top = gf.components.taper(length=taper_length, width1=width, width2=taper_width2, layer=layer)
    taper_right_top_ref = c << taper_right_top
    taper_right_top_ref.connect("o1", s_right_top_ref.ports["o2"])

    # Right bottom
    s_right_bottom = gf.components.bend_s(size=(right_dx, right_dy), cross_section=xs)
    s_right_bottom_ref = c << s_right_bottom
    s_right_bottom_ref.connect("o1", c.ports["o3"])

    taper_right_bottom = gf.components.taper(length=taper_length, width1=width, width2=taper_width2, layer=layer)
    taper_right_bottom_ref = c << taper_right_bottom
    taper_right_bottom_ref.connect("o1", s_right_bottom_ref.ports["o2"])

    return c

device = my_device()
device.write_gds("my_device.gds")