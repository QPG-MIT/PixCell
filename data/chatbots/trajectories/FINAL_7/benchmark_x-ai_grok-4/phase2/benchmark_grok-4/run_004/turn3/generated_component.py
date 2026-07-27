import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)
    width = 0.5
    xs = gf.cross_section.cross_section(width=width, layer=layer)

    # Outer racetrack ring using path extrusion
    p = gf.Path()
    L = 2.5
    R = 1.25
    p.append(gf.path.straight(length=L))
    p.append(gf.path.arc(radius=R, angle=180))
    p.append(gf.path.straight(length=L))
    p.append(gf.path.arc(radius=R, angle=180))
    ring = gf.path.extrude(p, xs)
    c << ring
    ring.move((-L / 2, -R))

    # Inner structures: two short coupler_straight components placed side by side
    length_inner = 1.2
    gap_inner = 0.3
    horizontal_gap = 0.2
    left_center_x = - (length_inner + horizontal_gap) / 2
    right_center_x = (length_inner + horizontal_gap) / 2
    y_center = (gap_inner + width) / 2

    cpl_left = c << gf.components.coupler_straight(
        length=length_inner, gap=gap_inner, cross_section=xs
    )
    cpl_left.move(
        origin=(length_inner / 2, y_center),
        destination=(left_center_x, 0)
    )

    cpl_right = c << gf.components.coupler_straight(
        length=length_inner, gap=gap_inner, cross_section=xs
    )
    cpl_right.move(
        origin=(length_inner / 2, y_center),
        destination=(right_center_x, 0)
    )

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")