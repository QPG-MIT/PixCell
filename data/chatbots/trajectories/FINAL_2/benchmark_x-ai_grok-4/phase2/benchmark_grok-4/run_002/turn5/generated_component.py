import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    width = 25.0
    center = width / 2
    y_peak = 10.0
    dy_inner = y_peak / 3
    y_v = y_peak - dy_inner

    s = width / 3
    half_base = s / 2

    centers_top = [0, s, 2 * s, 3 * s]

    points = [
        (center, 0),
        (centers_top[0], y_peak),
        (centers_top[0] + half_base, y_v),
        (centers_top[1], y_peak),
        (centers_top[1] + half_base, y_v),
        (centers_top[2], y_peak),
        (centers_top[2] + half_base, y_v),
        (centers_top[3], y_peak),
        (center, 0),
    ]

    c.add_polygon(points, layer=layer)

    return c

device = my_device()
device.write_gds("my_device.gds")