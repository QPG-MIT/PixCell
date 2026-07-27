import gdsfactory as gf

@gf.cell
def bottle_carrier_device():
    """
    Creates a device shaped like 4 bottles in a carrier/crate with
    a triangular point at the bottom.
    
    Features:
    - Rectangular crate body
    - 4 trapezoidal bottle necks (wider at top, narrower at bottom)
    - Triangular stake/point at the bottom
    
    Fits within [25, 10] μm footprint.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Main rectangular crate dimensions
    box_width = 20.0   # μm
    box_height = 5.0   # μm
    
    # Bottle neck parameters
    num_bottles = 4
    bottle_height = 4.0      # height above crate
    bottle_top_width = 2.2   # width at bottle opening (top)
    
    # Calculate spacing between bottle centers
    spacing = box_width / num_bottles  # 5.0 μm
    
    # Gap between bottles at crate level (creates V-shaped negative space)
    inter_bottle_gap = 0.4
    bottle_bottom_width = spacing - inter_bottle_gap  # 4.6 μm
    
    # Bottom triangular point parameters
    point_width = 2.0
    point_height = 1.0
    
    # Total bounding box: 20 x 10 μm
    
    # 1. Create main rectangular crate (centered at origin)
    crate = gf.components.rectangle(
        size=(box_width, box_height),
        layer=layer,
        centered=True
    )
    c << crate
    
    # 2. Create 4 bottle neck trapezoids
    # Each bottle is wider at top (opening) and narrower at bottom (shoulder)
    for i in range(num_bottles):
        # Center x-position for this bottle
        x_center = -box_width / 2 + spacing / 2 + i * spacing
        
        # Trapezoid vertices (counter-clockwise from bottom-left)
        # Wider at top, narrower at bottom creates the characteristic bottle shape
        bottle_polygon = [
            (x_center - bottle_bottom_width / 2, box_height / 2),                   # bottom-left
            (x_center + bottle_bottom_width / 2, box_height / 2),                   # bottom-right
            (x_center + bottle_top_width / 2, box_height / 2 + bottle_height),      # top-right
            (x_center - bottle_top_width / 2, box_height / 2 + bottle_height),      # top-left
        ]
        c.add_polygon(bottle_polygon, layer=layer)
    
    # 3. Create bottom triangular point (stake)
    point_polygon = [
        (-point_width / 2, -box_height / 2),       # top-left
        (point_width / 2, -box_height / 2),        # top-right
        (0, -box_height / 2 - point_height),       # bottom apex
    ]
    c.add_polygon(point_polygon, layer=layer)
    
    return c


# Generate and save the device
if __name__ == "__main__":
    device = bottle_carrier_device()
    device.write_gds("bottle_carrier.gds")
    print(f"Device dimensions: {device.size} μm")