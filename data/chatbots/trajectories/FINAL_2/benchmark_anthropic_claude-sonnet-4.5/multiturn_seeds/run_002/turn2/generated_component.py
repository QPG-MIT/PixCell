import gdsfactory as gf

@gf.cell
def factory_device():
    """
    Creates a factory-shaped device with four tapered chimneys.
    Footprint: approximately 25 x 10 microns
    """
    c = gf.Component()
    
    # Define dimensions based on footprint constraint [25, 10] microns
    total_width = 25.0
    total_height = 10.0
    
    # Main building body dimensions (large rectangle at bottom)
    building_width = 23.5
    building_height = 3.6
    
    # Chimney dimensions
    num_chimneys = 4
    chimney_height = 5.5
    chimney_top_width = 1.0  # Narrow at top
    chimney_bottom_width = 2.5  # Wide at bottom (where it meets building)
    
    # Bottom triangle dimensions
    triangle_base = 2.5
    triangle_height = 0.9
    
    # Calculate positions (build from bottom up)
    triangle_bottom = -total_height / 2
    building_bottom = triangle_bottom + triangle_height
    building_top = building_bottom + building_height
    chimney_top = building_top + chimney_height
    
    # Create main rectangular building body
    building = c << gf.components.rectangle(
        size=(building_width, building_height),
        layer=(1, 0),
        centered=True
    )
    building.move((0, building_bottom + building_height/2))
    
    # Create four evenly-spaced tapered chimneys
    # Calculate spacing to distribute chimneys evenly
    chimney_spacing = building_width / (num_chimneys + 1)
    
    for i in range(num_chimneys):
        # Calculate x position for each chimney
        x_pos = -building_width/2 + chimney_spacing * (i + 1)
        
        # Create trapezoid for tapered chimney (wider at bottom, narrower at top)
        points = [
            (x_pos - chimney_bottom_width/2, building_top),      # Bottom left
            (x_pos + chimney_bottom_width/2, building_top),      # Bottom right
            (x_pos + chimney_top_width/2, chimney_top),          # Top right
            (x_pos - chimney_top_width/2, chimney_top)           # Top left
        ]
        
        c.add_polygon(points, layer=(1, 0))
    
    # Create bottom triangular protrusion (pointing downward)
    triangle_points = [
        (-triangle_base/2, building_bottom),         # Top left
        (triangle_base/2, building_bottom),          # Top right
        (0, triangle_bottom)                         # Bottom point (downward)
    ]
    c.add_polygon(triangle_points, layer=(1, 0))
    
    return c

if __name__ == "__main__":
    # Create the device
    device = factory_device()
    
    # Save to GDS file
    device.write_gds("factory_device.gds")
    
    # Optional: display the device
    device.show()
    
    print("Factory device created successfully!")
    print(f"Bounding box: {device.bbox}")