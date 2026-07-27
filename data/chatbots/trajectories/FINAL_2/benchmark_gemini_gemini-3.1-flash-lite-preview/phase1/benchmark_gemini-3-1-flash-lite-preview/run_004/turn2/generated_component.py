import gdsfactory as gf

@gf.cell
def custom_device():
    """
    Creates a device composed of a central rectangular body 
    with overlapping fingers to ensure a seamless, single-body geometry.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define the main rectangular body
    # Center the body at (0,0). Dimensions: 20um width, 10um height.
    body = c << gf.components.rectangle(size=(20, 10), layer=layer, centered=True)
    
    # 2. Define the 'finger' component
    # We use a taper to create the trapezoidal shape.
    # Length of 3um, starting width 2um, ending width 1um.
    finger_template = gf.components.taper(length=3, width1=2.0, width2=1.0, layer=layer)
    
    # 3. Add the 4 upward fingers
    # The body extends to y=5 (top edge). 
    # To ensure connection, we place the fingers at y=4, so they overlap the body by 1um.
    top_positions = [-7.5, -2.5, 2.5, 7.5]
    for x_pos in top_positions:
        finger = c << finger_template
        finger.rotate(90)
        # Position: x=x_pos, y=4 (1um inside the rectangle)
        finger.move((x_pos, 4))
        
    # 4. Add the 1 downward finger
    # The body extends to y=-5 (bottom edge).
    # To ensure connection, we place the finger at y=-4, overlapping by 1um.
    bot_finger = c << finger_template
    bot_finger.rotate(-90)
    # Position: x=0, y=-4 (1um inside the rectangle)
    bot_finger.move((0, -4))
    
    return c

# Create and save the device
device = custom_device()
device.write_gds("device_layout.gds")

# Optional: Visualize
# device.show()