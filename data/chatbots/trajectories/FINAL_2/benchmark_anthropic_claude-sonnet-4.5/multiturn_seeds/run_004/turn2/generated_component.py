import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component()
    
    # Parameters based on footprint constraint [25, 10]
    total_width = 25.0
    total_height = 10.0
    
    # Base rectangle dimensions (should be smaller proportion)
    base_width = 25.0
    base_height = 3.5  # Reduced from 4.5
    base_y_start = 0.5  # Leave room for triangle below
    
    # Pillar dimensions (taller and narrower)
    num_pillars = 4
    pillar_height = 6.0  # Increased from 5.0
    pillar_bottom_width = 1.5  # Reduced from 2.0
    pillar_top_width = 0.3  # Reduced from 0.5
    
    # Triangle at bottom center
    triangle_height = 0.5
    triangle_base_width = 1.5
    
    # Create base rectangle
    base_points = [
        (0, base_y_start),
        (base_width, base_y_start),
        (base_width, base_y_start + base_height),
        (0, base_y_start + base_height)
    ]
    c.add_polygon(base_points, layer=(1, 0))
    
    # Create triangle protrusion at bottom center (pointing down)
    triangle_center_x = base_width / 2
    triangle_points = [
        (triangle_center_x - triangle_base_width/2, base_y_start),
        (triangle_center_x + triangle_base_width/2, base_y_start),
        (triangle_center_x, base_y_start - triangle_height)
    ]
    c.add_polygon(triangle_points, layer=(1, 0))
    
    # Create four tapered pillars on top of base
    # Calculate pillar positions - evenly spaced across width
    pillar_spacing = base_width / (num_pillars + 1)
    pillar_y_start = base_y_start + base_height
    
    for i in range(num_pillars):
        x_center = (i + 1) * pillar_spacing
        
        # Create trapezoid for each tapered pillar (wider at bottom, narrow at top)
        pillar_points = [
            (x_center - pillar_bottom_width/2, pillar_y_start),
            (x_center + pillar_bottom_width/2, pillar_y_start),
            (x_center + pillar_top_width/2, pillar_y_start + pillar_height),
            (x_center - pillar_top_width/2, pillar_y_start + pillar_height)
        ]
        
        c.add_polygon(pillar_points, layer=(1, 0))
    
    return c

# Create and save the device
device_component = device()
device_component.write_gds("device.gds")