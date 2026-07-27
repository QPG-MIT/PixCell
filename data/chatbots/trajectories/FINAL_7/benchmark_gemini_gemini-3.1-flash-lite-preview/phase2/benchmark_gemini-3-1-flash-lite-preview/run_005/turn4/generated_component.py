import gdsfactory as gf

@gf.cell
def get_stadium_component(width, height, layer=(1, 0)):
    """Creates a stadium shape by combining a rectangle and two circles."""
    c = gf.Component()
    rect_w = width - height
    
    # Add rectangular part
    c << gf.components.rectangle(size=(rect_w, height), layer=layer, centered=True)
    
    # Add semi-circles at both ends
    c1 = c << gf.components.circle(radius=height / 2, layer=layer)
    c1.movex(-rect_w / 2)
    
    c2 = c << gf.components.circle(radius=height / 2, layer=layer)
    c2.movex(rect_w / 2)
    
    return c

@gf.cell
def custom_device():
    c = gf.Component()
    
    # --- Dimensions ---
    total_w, total_h = 5.5, 3.0
    stroke = 0.4
    
    # Frame construction
    outer = get_stadium_component(width=total_w, height=total_h)
    inner = get_stadium_component(width=total_w - 2 * stroke, height=total_h - 2 * stroke)
    frame = gf.boolean(outer, inner, operation="not", layer=(1, 0))
    c << frame
    
    # --- Internal Structure ---
    # The structure consists of two rectangular blocks and two bars connecting them to the frame.
    # Block dimensions (taller than the bars)
    block_w, block_h = 1.2, 1.8
    # Connecting bar dimensions
    bar_w, bar_h = 0.95, 0.4
    gap = 0.4
    
    # Left side: Bar + Block
    b1 = c << gf.components.rectangle(size=(block_w, block_h), centered=True, layer=(1, 0))
    b1.movex(-(gap / 2 + block_w / 2))
    
    bar1 = c << gf.components.rectangle(size=(bar_w, bar_h), centered=True, layer=(1, 0))
    bar1.movex(-(gap / 2 + block_w + bar_w / 2))
    
    # Right side: Block + Bar
    b2 = c << gf.components.rectangle(size=(block_w, block_h), centered=True, layer=(1, 0))
    b2.movex((gap / 2 + block_w / 2))
    
    bar2 = c << gf.components.rectangle(size=(bar_w, bar_h), centered=True, layer=(1, 0))
    bar2.movex((gap / 2 + block_w + bar_w / 2))
    
    return c

# Generate and save
device = custom_device()
device.write_gds("device.gds")
# device.show() # Uncomment to view the resulting GDS