import gdsfactory as gf

@gf.cell
def get_stadium_component(width, height):
    """Creates a new component containing the stadium shape."""
    c = gf.Component()
    rect_w = width - height
    
    # Add primitives to the component
    c << gf.components.rectangle(size=(rect_w, height), centered=True)
    c1 = c << gf.components.circle(radius=height / 2)
    c1.movex(-rect_w / 2)
    c2 = c << gf.components.circle(radius=height / 2)
    c2.movex(rect_w / 2)
    return c

@gf.cell
def custom_device():
    c = gf.Component()
    
    # Dimensions based on footprint [3.0, 5.5]
    total_w, total_h = 5.5, 3.0
    stroke = 0.4
    
    # 1. Create Frame (outer - inner)
    outer_stadium = get_stadium_component(width=total_w, height=total_h)
    inner_stadium = get_stadium_component(width=total_w - 2 * stroke, height=total_h - 2 * stroke)
    frame = gf.boolean(outer_stadium, inner_stadium, operation="not", layer=(1, 0))
    
    # 2. Create Inner Rectangles Component
    rect_size = (1.2, 1.8)
    gap = 0.4
    rects = gf.Component("rects")
    
    r1 = rects << gf.components.rectangle(size=rect_size, centered=True)
    r1.movex(-(rect_size[0] / 2 + gap / 2))
    
    r2 = rects << gf.components.rectangle(size=rect_size, centered=True)
    r2.movex((rect_size[0] / 2 + gap / 2))
    
    # 3. Create Bridges Component
    bridge_w, bridge_h = 0.4, 0.2
    bridges = gf.Component("bridges")
    
    # Helper to add bridges at specific locations
    def add_bridge(x, y):
        b = bridges << gf.components.rectangle(size=(bridge_w, bridge_h), centered=True)
        b.move((x, y))
        
    add_bridge(-(rect_size[0]/2 + gap/2), rect_size[1]/2 + bridge_h/2)
    add_bridge(-(rect_size[0]/2 + gap/2), -(rect_size[1]/2 + bridge_h/2))
    add_bridge((rect_size[0]/2 + gap/2), rect_size[1]/2 + bridge_h/2)
    add_bridge((rect_size[0]/2 + gap/2), -(rect_size[1]/2 + bridge_h/2))
    
    # 4. Final Boolean Union
    # Combine frame + rects + bridges into one final component
    device = gf.boolean(frame, rects, operation="or", layer=(1, 0))
    device = gf.boolean(device, bridges, operation="or", layer=(1, 0))
    
    return device

# Generate, save, and show
device = custom_device()
device.write_gds("device.gds")
device.show()