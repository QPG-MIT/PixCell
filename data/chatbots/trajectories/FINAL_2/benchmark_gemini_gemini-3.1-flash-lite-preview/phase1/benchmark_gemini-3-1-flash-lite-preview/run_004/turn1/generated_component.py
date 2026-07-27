import gdsfactory as gf

@gf.cell
def custom_device():
    """
    Creates a device composed of a main body and multiple protruding fingers
    using GDSFactory parametric primitives and boolean operations.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define the main rectangular body
    # Footprint constraint: 25um x 10um. We use a 20x4 rectangle as the body.
    body = gf.components.rectangle(size=(20, 4), layer=layer, centered=True)
    
    # 2. Define the 'finger' component
    # We use a taper to create the slightly flared vertical shape
    finger = gf.components.taper(length=3, width1=2.0, width2=1.5, layer=layer)
    
    # Initialize the combined shape with the body
    combined = body
    
    # 3. Add the 4 upward fingers
    # Placed evenly along the top edge of the body
    top_positions = [-7.5, -2.5, 2.5, 7.5]
    for x_pos in top_positions:
        # Create a reference for the finger
        f_ref = gf.Component()
        f_ref_instance = f_ref << finger
        f_ref_instance.rotate(90)
        # Position at top edge (y=2 is half the body height of 4)
        # Offset by half the length of the taper (1.5) to align correctly
        f_ref_instance.move((x_pos, 2 + 1.5))
        
        # Boolean union: Combine with existing geometry
        combined = gf.boolean(combined, f_ref, operation="or", layer=layer)
        
    # 4. Add the 1 downward finger
    # Positioned at the center bottom
    bot_ref = gf.Component()
    bot_ref_instance = bot_ref << finger
    bot_ref_instance.rotate(-90)
    # Position at bottom edge (y=-2)
    bot_ref_instance.move((0, -2 - 1.5))
    
    # Final Boolean union
    final_shape = gf.boolean(combined, bot_ref, operation="or", layer=layer)
    
    # Add to component
    c << final_shape
    
    return c

# Create and save the device
device = custom_device()
device.write_gds("device_layout.gds")

# Optional: Visualize the output
# device.show()