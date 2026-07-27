import gdsfactory as gf

@gf.cell
def my_device():
    layer = (1, 0)
    width = 25.0
    h_bottom = 1.0
    h_rect = 3.0
    h_top = 6.0
    b_top = 3.0
    b_bottom = 3.0
    center_x = width / 2
    pitch = 5.0
    centers = [5.0, 10.0, 15.0, 20.0]

    # Rectangle component, positioned
    rect_comp = gf.Component()
    rect_ref = rect_comp << gf.components.rectangle(size=(width, h_rect), layer=layer, centered=True)
    rect_ref.move((center_x, h_bottom + h_rect / 2))

    # Bottom triangle component, pointed down, positioned
    tri_bottom_comp = gf.Component()
    tri_bottom_ref = tri_bottom_comp << gf.components.triangle(x=b_bottom, y=h_bottom, layer=layer)
    tri_bottom_ref.rotate(180)
    tri_bottom_ref.move((center_x + b_bottom / 2, h_bottom))

    # Top triangle components
    top_comps = []
    for cent in centers:
        top_comp = gf.Component()
        top_ref = top_comp << gf.components.triangle(x=b_top, y=h_top, layer=layer)
        top_ref.move((cent - b_top / 2, h_bottom + h_rect))
        top_comps.append(top_comp)

    # Iteratively union all parts
    combined = rect_comp
    combined = gf.boolean(combined, tri_bottom_comp, operation="or", layer=layer)
    for top in top_comps:
        combined = gf.boolean(combined, top, operation="or", layer=layer)

    return combined

device = my_device()
device.write_gds("my_device.gds")