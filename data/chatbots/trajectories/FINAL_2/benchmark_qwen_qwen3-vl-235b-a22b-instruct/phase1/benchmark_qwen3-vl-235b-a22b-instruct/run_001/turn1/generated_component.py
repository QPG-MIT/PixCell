import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    
    # Define layer
    layer = (1, 0)
    
    # Create base rectangle (25μm x 10μm)
    base = gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    base_ref = c << base
    
    # Create top fingers (4 fingers)
    finger_width = 1.5  # width of each finger
    finger_height = 3.0  # height of each finger
    spacing = 5.0  # spacing between fingers
    
    # Position the four fingers at the top
    for i in range(4):
        finger = gf.components.rectangle(size=(finger_width, finger_height), layer=layer)
        finger_ref = c << finger
        # Position at top, with spacing
        x_pos = -12.5 + (i + 0.5) * spacing  # Centered horizontally
        y_pos = 5.0 + finger_height / 2  # At the top edge
        finger_ref.move((x_pos, y_pos))
    
    # Create bottom notch (inverted finger)
    notch_width = 1.5
    notch_height = 2.0
    
    notch = gf.components.rectangle(size=(notch_width, notch_height), layer=layer)
    notch_ref = c << notch
    # Position at bottom center
    notch_ref.move((0, -5.0 - notch_height / 2))  # At the bottom edge, centered
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")