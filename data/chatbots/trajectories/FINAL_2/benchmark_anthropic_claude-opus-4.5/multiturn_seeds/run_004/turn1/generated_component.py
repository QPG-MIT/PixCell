import gdsfactory as gf

@gf.cell
def bottle_crate():
    """
    Creates a stylized bottle crate icon with 4 bottles and a V-notch pointer.
    Fits within footprint of [25, 10] micrometers.
    """
    c = gf.Component()
    
    # Main crate body dimensions
    body_width = 10.0
    body_height = 5.0
    body_x = 1.0  # Left offset
    body_y = 0.5  # Bottom offset for V-notch
    
    # Bottle parameters
    num_bottles = 4
    bottle_height = 4.0
    bottle_top_width = 1.2    # Wider at top (bottle mouth)
    bottle_bottom_width = 0.5  # Narrower at bottom (neck)
    
    # Calculate bottle positions (evenly spaced within body)
    edge_margin = 0.15
    first_bottle_x = body_x + bottle_top_width/2 + edge_margin
    last_bottle_x = body_x + body_width - bottle_top_width/2 - edge_margin
    bottle_spacing = (last_bottle_x - first_bottle_x) / (num_bottles - 1)
    
    # V-notch parameters (pointing downward)
    notch_width = 1.2
    notch_depth = 0.5
    
    # Create main crate body rectangle
    c.add_polygon([
        (body_x, body_y),
        (body_x + body_width, body_y),
        (body_x + body_width, body_y + body_height),
        (body_x, body_y + body_height)
    ], layer=(1, 0))
    
    # Create bottle necks (trapezoids - narrow at base, wider at top)
    bottle_base_y = body_y + body_height
    for i in range(num_bottles):
        cx = first_bottle_x + i * bottle_spacing
        c.add_polygon([
            (cx - bottle_bottom_width/2, bottle_base_y),
            (cx + bottle_bottom_width/2, bottle_base_y),
            (cx + bottle_top_width/2, bottle_base_y + bottle_height),
            (cx - bottle_top_width/2, bottle_base_y + bottle_height)
        ], layer=(1, 0))
    
    # Create V-notch pointing downward at bottom center
    center_x = body_x + body_width / 2
    c.add_polygon([
        (center_x - notch_width/2, body_y),
        (center_x + notch_width/2, body_y),
        (center_x, body_y - notch_depth)
    ], layer=(1, 0))
    
    return c

# Create and save the device
device = bottle_crate()
device.write_gds("bottle_crate.gds")