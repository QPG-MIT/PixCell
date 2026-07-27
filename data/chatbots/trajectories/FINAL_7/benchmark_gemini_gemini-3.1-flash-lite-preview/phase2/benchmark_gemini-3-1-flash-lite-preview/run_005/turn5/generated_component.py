import gdsfactory as gf

@gf.cell
def get_stadium(width, height, layer=(1, 0)):
    """Creates a stadium shape by combining a rectangle and two circles."""
    c = gf.Component()
    r = height / 2
    # The straight part is a rectangle of (width - height)
    rect = c << gf.components.rectangle(size=(width - height, height), centered=True, layer=layer)
    # The ends are two semi-circles
    c1 = c << gf.components.circle(radius=r, layer=layer)
    c1.movex(-(width - height) / 2)
    c2 = c << gf.components.circle(radius=r, layer=layer)
    c2.movex((width - height) / 2)
    return c

@gf.cell
def custom_device():
    c = gf.Component()
    
    # --- Dimensions ---
    total_w, total_h = 5.5, 3.0
    stroke = 0.35
    
    # Frame construction using boolean "not"
    outer = get_stadium(width=total_w, height=total_h)
    inner = get_stadium(width=total_w - 2 * stroke, height=total_h - 2 * stroke)
    frame = gf.boolean(outer, inner, operation="not", layer=(1, 0))
    c << frame
    
    # --- Internal Structure ---
    # The structure consists of a center block and two bars connecting to the frame
    block_w, block_h = 1.2, 1.2
    bar_h = 0.5
    
    # Calculate cavity dimensions to ensure bars reach the frame
    cavity_w = total_w - 2 * stroke
    bar_w = (cavity_w - block_w) / 2
    
    # Vertical offset for the two mirrored structures
    y_offset = 0.6
    
    def add_structure(y):
        # Central Block
        b = c << gf.components.rectangle(size=(block_w, block_h), centered=True, layer=(1, 0))
        b.movey(y)
        
        # Left Bar
        left_bar = c << gf.components.rectangle(size=(bar_w, bar_h), centered=True, layer=(1, 0))
        left_bar.movex(-(block_w / 2 + bar_w / 2))
        left_bar.movey(y)
        
        # Right Bar
        right_bar = c << gf.components.rectangle(size=(bar_w, bar_h), centered=True, layer=(1, 0))
        right_bar.movex((block_w / 2 + bar_w / 2))
        right_bar.movey(y)

    # Add top and bottom structures
    add_structure(y_offset)
    add_structure(-y_offset)
    
    return c

# Generate and save
device = custom_device()
device.write_gds("device.gds")