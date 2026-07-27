import gdsfactory as gf

def simple_horizontal_rectangle_device():
    c = gf.Component()
    
    # Create a horizontal rectangle matching the footprint constraint
    # Size is (width, height) = (120.0, 4.0)
    rect = c << gf.components.rectangle(size=(120.0, 4.0), layer=(1, 0), centered=False)
    
    # Position the rectangle at origin
    rect.move((0, 0))
    
    # Add ports at the left and right ends using the component's layer
    layer = (1, 0)
    
    # Create ports at the center of the left and right edges
    left_port = gf.Port(
        name="o1", 
        center=(0, 2.0),  # center of left edge (y = height/2)
        width=4.0, 
        orientation=180,
        layer=layer
    )
    right_port = gf.Port(
        name="o2", 
        center=(120.0, 2.0),  # center of right edge (x = length, y = height/2)
        width=4.0, 
        orientation=0,
        layer=layer
    )
    
    c.add_port("o1", port=left_port)
    c.add_port("o2", port=right_port)
    
    return c

# Create and save the device
device = simple_horizontal_rectangle_device()
device.write_gds("simple_horizontal_rectangle.gds")