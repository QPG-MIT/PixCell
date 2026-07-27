import gdsfactory as gf

@gf.cell
def get_stadium(width, height, layer=(1, 0)):
    """Creates a stadium shape by combining a rectangle and two circles."""
    c = gf.Component()
    rect_w = width - height
    
    # Create primitives. Rectangle is centered by default.
    rect = c << gf.components.rectangle(size=(rect_w, height), layer=layer, centered=True)
    
    # Circles are centered at (0,0) by default. Move them to the ends.
    c1 = c << gf.components.circle(radius=height / 2, layer=layer)
    c1.movex(-rect_w / 2)
    
    c2 = c << gf.components.circle(radius=height / 2, layer=layer)
    c2.movex(rect_w / 2)
    
    return c

@gf.cell
def custom_device():
    c = gf.Component()
    
    # Dimensions based on footprint [3.0, 5.5]
    total_w = 5.5
    total_h = 3.0
    stroke = 0.4
    
    # 1. Create the Outer Frame using boolean 'not'
    outer = get_stadium(width=total_w, height=total_h)
    inner = get_stadium(width=total_w - 2 * stroke, height=total_h - 2 * stroke)
    frame = c << gf.boolean(outer, inner, operation="not", layer=(1, 0))
    
    # 2. Define Inner Rectangles
    inner_rect_size = (1.2, 1.8)
    gap = 0.4
    
    # Create the two blocks
    rect_left = c << gf.components.rectangle(size=inner_rect_size, centered=True, layer=(1, 0))
    rect_left.move((- (inner_rect_size[0]/2 + gap/2), 0))
    
    rect_right = c << gf.components.rectangle(size=inner_rect_size, centered=True, layer=(1, 0))
    rect_right.move((inner_rect_size[0]/2 + gap/2, 0))
    
    # 3. Create Connecting Bars (Bridges)
    conn_w = 0.3
    conn_h = 0.5
    
    # Place bridges connecting the rectangles to the top/bottom of the frame
    # Bridges are placed at y=+-0.5 to touch the inner frame edges
    for x_pos in [- (inner_rect_size[0]/2 + gap/2), (inner_rect_size[0]/2 + gap/2)]:
        for y_sign in [-1, 1]:
            bridge = c << gf.components.rectangle(size=(conn_w, conn_h), centered=True, layer=(1, 0))
            bridge.move((x_pos, y_sign * (inner_rect_size[1]/2 + conn_h/2)))

    return c

# Create, visualize, and save
device = custom_device()
device.show()
device.write_gds("device.gds")