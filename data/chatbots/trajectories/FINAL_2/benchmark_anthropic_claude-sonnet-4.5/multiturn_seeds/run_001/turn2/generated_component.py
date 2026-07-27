import gdsfactory as gf

@gf.cell
def factory_device():
    c = gf.Component()
    
    # Device dimensions to fit within 25x10 um footprint
    total_width = 25
    total_height = 10
    
    # Main body rectangle (large building base)
    body_width = 24.5
    body_height = 5.3
    body_x = (total_width - body_width) / 2
    body_y = 1.0
    
    body = c << gf.components.rectangle(
        size=(body_width, body_height),
        layer=(1, 0),
        centered=False
    )
    body.move((body_x, body_y))
    
    # Bottom triangular support/foundation (pointing downward)
    triangle_width = 3.0
    triangle_height = 1.0
    triangle_x_center = total_width / 2
    
    triangle_points = [
        (triangle_x_center - triangle_width/2, body_y),
        (triangle_x_center + triangle_width/2, body_y),
        (triangle_x_center, 0)
    ]
    c.add_polygon(triangle_points, layer=(1, 0))
    
    # Four tapered chimneys/smokestacks (wider at bottom, narrower at top)
    num_chimneys = 4
    chimney_total_height = 3.7
    chimney_top_width = 1.6
    chimney_bottom_width = 2.4
    
    # Starting position for chimneys
    chimney_base_y = body_y + body_height
    
    # Calculate positions for 4 evenly spaced chimneys
    # Chimneys are positioned with equal spacing between their centers
    chimney_spacing = 6.2
    # Start position so all 4 are centered
    start_x = (total_width - (3 * chimney_spacing)) / 2
    
    for i in range(num_chimneys):
        x_center = start_x + chimney_spacing * i
        
        # Create tapered chimney as trapezoid (narrowing upward)
        chimney_points = [
            (x_center - chimney_bottom_width/2, chimney_base_y),
            (x_center + chimney_bottom_width/2, chimney_base_y),
            (x_center + chimney_top_width/2, chimney_base_y + chimney_total_height),
            (x_center - chimney_top_width/2, chimney_base_y + chimney_total_height)
        ]
        c.add_polygon(chimney_points, layer=(1, 0))
    
    return c

# Create and save the device
device = factory_device()
device.write_gds("factory_device.gds")
print("Factory device GDS file created successfully!")