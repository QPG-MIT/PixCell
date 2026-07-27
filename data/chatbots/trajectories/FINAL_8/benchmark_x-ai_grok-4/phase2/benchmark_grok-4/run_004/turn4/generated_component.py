import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)
    dx = 20.0
    middle_length = 80.0

    top = gf.Component()

    def add_curved_strip(comp, dx, middle_length, xs, y_middle, dy):
        strip = gf.Component()
        left = gf.components.bend_s(size=(dx, dy), cross_section=xs)
        l = strip << left
        stra = gf.components.straight(length=middle_length, cross_section=xs)
        s = strip << stra
        s.connect("o1", l.ports["o2"])
        right = gf.components.bend_s(size=(dx, -dy), cross_section=xs)
        r = strip << right
        r.connect("o1", s.ports["o2"])
        ref = comp << strip
        ref.move((0, y_middle - dy))

    # Parameters for solid
    num_solid = 5
    y_start_solid = 0.0
    step_solid = 0.15
    dy_start_solid = 0.1
    dy_step_solid = 0.05
    width_solid = 0.25

    for i in range(num_solid):
        y_middle = y_start_solid + i * step_solid
        dy = dy_start_solid + i * dy_step_solid
        xs = gf.cross_section.cross_section(width=width_solid, layer=layer)
        add_curved_strip(top, dx, middle_length, xs, y_middle, dy)

    # Parameters for thin
    num_thin = 4
    y_start_thin = y_start_solid + (num_solid - 1) * step_solid + step_solid
    step_thin = 0.3
    dy_start_thin = dy_start_solid + (num_solid - 1) * dy_step_solid + 0.1
    dy_step_thin = 0.1
    width_thin = 0.1

    for i in range(num_thin):
        y_middle = y_start_thin + i * step_thin
        dy = dy_start_thin + i * dy_step_thin
        xs = gf.cross_section.cross_section(width=width_thin, layer=layer)
        add_curved_strip(top, dx, middle_length, xs, y_middle, dy)

    # Add to main component
    top_ref = c << top
    bottom_ref = c << top
    bottom_ref.mirror(p1=(0, 0), p2=(1, 0))
    bottom_ref.move((0, 0.2))

    return c

device = my_device()
device.write_gds("my_device.gds")