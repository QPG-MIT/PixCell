import gdsfactory as gf

@gf.cell
def tapering_s_bend(dx: float, dy: float, w_start: float, w_end: float, layer: tuple = (1, 0)) -> gf.Component:
    c = gf.Component()
    control_points = [
        (0, 0),
        (dx * 0.25, 0),
        (dx * 0.75, dy),
        (dx, dy),
    ]
    path = gf.path.bezier(control_points=control_points)
    xs1 = gf.cross_section.cross_section(width=w_start, layer=layer)
    xs2 = gf.cross_section.cross_section(width=w_end, layer=layer)
    trans = gf.path.transition(xs1, xs2, width_type='sine')
    element = gf.path.extrude_transition(path, trans)
    ref = c << element
    c.add_port("o1", port=ref.ports["o1"] if "o1" in ref.ports else gf.Port(name="o1", center=(0, 0), width=w_start, orientation=180, layer=layer))
    c.add_port("o2", port=ref.ports["o2"] if "o2" in ref.ports else gf.Port(name="o2", center=(dx, dy), width=w_end, orientation=0, layer=layer))
    return c

@gf.cell
def my_device() -> gf.Component:
    c = gf.Component()
    layer = (1, 0)
    l_left = 4.0
    w_left = 0.4
    gap = 0.2
    l_stem = 2.0
    w_mid = 0.6
    dx = 33.8
    target_dy = 1.7 / 2
    w_start = w_mid / 2
    shift = w_mid / 4
    dy_path_upper = target_dy - shift
    dy_path_lower = -target_dy - (-shift)
    min_width = 0.002
    # Left taper
    left = gf.components.taper(length=l_left, width1=w_left, width2=min_width)
    left_ref = c << left
    # Stem
    stem = gf.components.taper(length=l_stem, width1=min_width, width2=w_mid)
    stem_ref = c << stem
    stem_ref.move((l_left + gap, 0))
    # Upper arm
    upper_arm = tapering_s_bend(dx=dx, dy=dy_path_upper, w_start=w_start, w_end=min_width, layer=layer)
    upper_ref = c << upper_arm
    upper_ref.connect("o1", stem_ref.ports["o2"])
    upper_ref.move((0, shift))
    # Lower arm
    lower_arm = tapering_s_bend(dx=dx, dy=dy_path_lower, w_start=w_start, w_end=min_width, layer=layer)
    lower_ref = c << lower_arm
    lower_ref.connect("o1", stem_ref.ports["o2"])
    lower_ref.move((0, -shift))
    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")