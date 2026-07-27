import gdsfactory as gf

@gf.cell
def fan(rx=60.0, ry=1.5, d=0.25, num_lines=4, layer=(1, 0)):
    f = gf.Component()
    max_rx = rx + num_lines * d
    max_ry = ry + num_lines * d
    # Cut for upper half
    cut_size = (120, max_ry + 1)
    cut_rect = gf.components.rectangle(size=cut_size, layer=layer, centered=True)
    cut_comp = gf.Component()
    cut_ref = cut_comp << cut_rect
    cut_ref.move((0, (max_ry + 1) / 2))
    # Inner
    inner_e = gf.components.ellipse(radii=(rx, ry), layer=layer)
    half_inner = gf.boolean(inner_e, cut_comp, "and", layer=layer)
    f.add_ref(half_inner)
    # Rings
    current_rx = rx
    current_ry = ry
    for i in range(num_lines):
        outer_rx = current_rx + d
        outer_ry = current_ry + d
        outer_e = gf.components.ellipse(radii=(outer_rx, outer_ry), layer=layer)
        inner_e = gf.components.ellipse(radii=(current_rx, current_ry), layer=layer)
        ring = gf.boolean(outer_e, inner_e, "not", layer=layer)
        half_ring = gf.boolean(ring, cut_comp, "and", layer=layer)
        f.add_ref(half_ring)
        current_rx = outer_rx
        current_ry = outer_ry
    return f

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)
    rx = 60.0
    ry = 0.8
    num_lines = 3
    d = 0.4
    max_ry = ry + num_lines * d
    top = c << fan(rx, ry, d, num_lines, layer)
    bottom = c << fan(rx, ry, d, num_lines, layer)
    bottom.mirror(p1=(0, 0), p2=(1, 0))
    # Small triangle at bottom right
    tri = c << gf.components.triangle(x=1, y=1, layer=layer)
    tri.rotate(90)
    tri.move((59, 0.5))
    return c

device = my_device()
device.write_gds("my_device.gds")