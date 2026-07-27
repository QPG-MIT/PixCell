import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)
    
    # Define dimensions based on 25x10 footprint
    total_width = 25.0
    total_height = 10.0
    
    # Main rectangle base (occupies most of the footprint)
    base_height = 8.0  # Height of the main rectangle
    base_width = total_width
    base = c << gf.components.rectangle(size=(base_width, base_height), layer=layer, centered=False)
    base.move((0, 0))  # Position at bottom left corner for easier alignment
    
    # Calculate positions for the four fingers
    finger_width = 1.0
    finger_height = 2.0  # Extend above the base
    spacing = (total_width - 4 * finger_width) / 5  # Equal spacing between fingers
    
    # Create and position the four fingers
    for i in range(4):
        x_pos = spacing + i * (finger_width + spacing)
        finger = c << gf.components.rectangle(size=(finger_width, finger_height), layer=layer)
        finger.move((x_pos, base_height))  # Position at top of base
    
    # Create the bottom triangular point
    # Triangle pointing downward from center bottom
    triangle_width = 2.0
    triangle_height = 2.0
    triangle = c << gf.components.triangle(x=triangle_width, y=triangle_height, layer=layer)
    triangle.move((total_width/2 - triangle_width/2, -triangle_height))  # Position at bottom center
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")