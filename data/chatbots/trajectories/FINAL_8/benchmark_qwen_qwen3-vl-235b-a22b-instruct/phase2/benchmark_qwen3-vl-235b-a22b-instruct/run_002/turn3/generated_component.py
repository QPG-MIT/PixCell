import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define layer
    layer = (1, 0)
    
    # Define dimensions for the rectangles
    bar_width = 120.0  # matches footprint constraint
    bar_height = 4.0   # matches footprint constraint
    spacing = 20.0     # vertical spacing between bars
    
    # Create 3 horizontal bars
    for i in range(3):
        # Calculate y position for each bar
        y_position = i * (bar_height + spacing)
        
        # Create rectangle
        rect = c << gf.components.rectangle(
            size=(bar_width, bar_height), 
            layer=layer, 
            centered=False
        )
        
        # Position the rectangle
        rect.move((0, y_position))
        
        # Add ports for external connections (optional, if needed)
        c.add_port(f"left_{i+1}", port=rect.ports["e1"])
        c.add_port(f"right_{i+1}", port=rect.ports["e2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")