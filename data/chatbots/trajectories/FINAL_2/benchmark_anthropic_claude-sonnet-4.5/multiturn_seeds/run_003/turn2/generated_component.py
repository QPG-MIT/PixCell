import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    
    # Define dimensions based on 25x10 um footprint
    total_width = 25.0
    total_height = 10.0
    
    # Base rectangle dimensions (large bottom block)
    base_width = 23.0  # ~92% of total width
    base_height = 6.0  # 60% of total height
    base_y_bottom = 0.3  # Leave space for triangle
    
    # Create main base rectangle
    base = c << gf.components.rectangle(
        size=(base_width, base_height),
        layer=(1, 0),
        centered=True
    )
    base.movey(base_y_bottom + base_height/2)
    
    # Pillar/chimney parameters (4 vertical structures on top)
    num_pillars = 4
    
    # Each pillar has three sections: bottom pad, thin middle, wide top
    pillar_bottom_width = 1.2
    pillar_bottom_height = 0.35
    
    pillar_middle_width = 0.35  # Very thin connector
    pillar_middle_height = 2.45
    
    pillar_top_width = 2.2
    pillar_top_height = 1.2
    
    # Calculate evenly spaced pillar positions across the base
    # 4 pillars with equal spacing
    pillar_spacing = base_width / 5.0  # Creates 5 gaps for 4 pillars
    
    for i in range(num_pillars):
        x_pos = -base_width/2 + pillar_spacing * (i + 1)
        y_base = base_y_bottom + base_height
        
        # Bottom pad of pillar (where it connects to base)
        pillar_bottom = c << gf.components.rectangle(
            size=(pillar_bottom_width, pillar_bottom_height),
            layer=(1, 0),
            centered=True
        )
        pillar_bottom.move((x_pos, y_base + pillar_bottom_height/2))
        
        # Middle section (very thin connector)
        pillar_middle = c << gf.components.rectangle(
            size=(pillar_middle_width, pillar_middle_height),
            layer=(1, 0),
            centered=True
        )
        pillar_middle.move((x_pos, y_base + pillar_bottom_height + pillar_middle_height/2))
        
        # Top section (wide cap)
        pillar_top = c << gf.components.rectangle(
            size=(pillar_top_width, pillar_top_height),
            layer=(1, 0),
            centered=True
        )
        pillar_top.move((x_pos, y_base + pillar_bottom_height + pillar_middle_height + pillar_top_height/2))
    
    # Bottom triangle protrusion (pointing downward from center bottom)
    triangle_width = 1.8
    triangle_height = 0.6
    
    # Create triangle pointing down
    triangle_points = [
        (-triangle_width/2, base_y_bottom),  # Top left (connects to base)
        (triangle_width/2, base_y_bottom),   # Top right (connects to base)
        (0, base_y_bottom - triangle_height),  # Bottom point
    ]
    
    c.add_polygon(triangle_points, layer=(1, 0))
    
    return c

# Create and save the device
device = device()
device.write_gds("device.gds")
print("Device GDS file created successfully!")