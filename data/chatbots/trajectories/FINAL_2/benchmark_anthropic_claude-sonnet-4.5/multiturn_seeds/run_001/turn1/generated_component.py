import gdsfactory as gf

@gf.cell
def factory_device():
    c = gf.Component()
    
    # Device dimensions to fit within 25x10 um footprint
    total_width = 25
    total_height = 10
    
    # Main body rectangle (large building base)
    body_width = 23.5
    body_height = 4.4
    body_x = (total_width - body_width) / 2
    body_y = 1.3
    
    body = c << gf.components.rectangle(
        size=(body_width, body_height),
        layer=(1, 0),
        centered=False
    )
    body.move((body_x, body_y))
    
    # Bottom triangular support/foundation
    triangle_width = 3.5
    triangle_height = 1.3
    triangle_x_center = total_width / 2
    
    triangle_points = [
        (triangle_x_center - triangle_width/2, body_y),
        (triangle_x_center + triangle_width/2, body_y),
        (triangle_x_center, 0)
    ]
    c.add_polygon(triangle_points, layer=(1, 0))
    
    # Four tapered chimneys/smokestacks
    num_chimneys = 4
    chimney_total_height = 4.3
    chimney_top_width = 1.4
    chimney_bottom_width = 2.8
    
    # Starting position for chimneys
    chimney_base_y = body_y + body_height
    
    # Calculate evenly spaced positions for 4 chimneys
    effective_width = body_width - 2
    spacing = effective_width / (num_chimneys - 1)
    start_x = body_x + 1
    
    for i in range(num_chimneys):
        x_center = start_x + spacing * i
        
        # Create tapered chimney as trapezoid
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