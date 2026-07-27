import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    bottom_height = 1.5
    rect_height = 2
    top_height = 6.5
    rect_width = 25
    bottom_base = 3
    top_base = 3
    centers_top = [5, 10, 15, 20]
    center_bottom = 12.5

    # Central rectangle
    rect = gf.components.rectangle(size=(rect_width, rect_height), layer=layer, centered=False)
    rect_ref = c << rect
    rect_ref.move((0, bottom_height))

    # Bottom taper (inverted triangle)
    tri_bottom = gf.components.triangle(x=bottom_base, y=bottom_height, layer=layer)
    tri_b_ref = c << tri_bottom
    tri_b_ref.mirror((0, 0), (1, 0))
    tri_b_ref.move((bottom_base / 2, -bottom_height), (center_bottom, 0))

    # Top tapers (triangles)
    for center in centers_top:
        tri_top = gf.components.triangle(x=top_base, y=top_height, layer=layer)
        tri_t_ref = c << tri_top
        tri_t_ref.move((top_base / 2, 0), (center, bottom_height + rect_height))

    return c

device = my_device()
device.write_gds("my_device.gds")