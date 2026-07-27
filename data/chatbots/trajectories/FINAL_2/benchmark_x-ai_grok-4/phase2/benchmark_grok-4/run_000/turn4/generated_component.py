import gdsfactory as gf

def isosceles_triangle(base, height, layer):
    half = base / 2.0
    c = gf.Component()
    tri1 = c << gf.components.triangle(x=half, y=height, layer=layer)
    tri2 = c << gf.components.triangle(x=half, y=height, layer=layer)
    tri2.mirror(p1=(0, 0), p2=(0, 1))
    return c

@gf.cell
def my_device():
    layer = (1, 0)
    width = 25.0
    h_bottom = 2.5
    h_rect = 2.0
    h_top = 5.5
    b_top = 10.0
    b_bottom = 5.0
    half = b_top / 2
    s = (width - b_top) / 3
    centers = [half + i * s for i in range(4)]
    center_x = width / 2

    # Rectangle component
    rect_comp = gf.Component()
    rect = gf.components.rectangle(size=(width, h_rect), layer=layer, centered=False)
    rect_ref = rect_comp << rect
    rect_ref.move((0, h_bottom))

    # Bottom triangle component
    bottom_comp = gf.Component()
    bottom_tri = isosceles_triangle(b_bottom, h_bottom, layer)
    bottom_ref = bottom_comp << bottom_tri
    bottom_ref.rotate(180)
    bottom_ref.move((center_x, h_bottom))

    # Union rectangle and bottom
    combined = gf.boolean(rect_comp, bottom_comp, operation="or", layer=layer)

    # Top triangle components
    for cent in centers:
        top_comp = gf.Component()
        top_tri = isosceles_triangle(b_top, h_top, layer)
        top_ref = top_comp << top_tri
        top_ref.move((cent, h_bottom + h_rect))
        combined = gf.boolean(combined, top_comp, operation="or", layer=layer)

    return combined

device = my_device()
device.write_gds("my_device.gds")