import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    bottom_height = 2.5
    rect_height = -0.5
    top_height = 8
    rect_width = 25
    bottom_base = 25
    centers_top = [3.125, 9.375, 15.625, 21.875]
    center_bottom = 12.5

    y_bottom = bottom_height
    y_valley = bottom_height + rect_height
    y_peak = bottom_height + rect_height + top_height
    x_left = 0
    x_right = rect_width
    half_base = 6.25 / 2

    points = [
        (x_left, y_bottom),
        (centers_top[0], y_peak),
        (centers_top[0] + half_base, y_valley),
        (centers_top[1], y_peak),
        (centers_top[1] + half_base, y_valley),
        (centers_top[2], y_peak),
        (centers_top[2] + half_base, y_valley),
        (centers_top[3], y_peak),
        (x_right, y_bottom),
        (center_bottom + bottom_base / 2, y_bottom),
        (center_bottom, 0),
        (center_bottom - bottom_base / 2, y_bottom),
    ]

    c.add_polygon(points, layer=layer)

    return c

device = my_device()
device.write_gds("my_device.gds")