import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)  # Default layer
    
    # Main rectangular body (footprint is 25x10, so we'll use most of that)
    main_width = 25.0
    main_height = 8.0  # Leave some space for the upward fingers
    main_rect = gf.components.rectangle(size=(main_width, main_height), layer=layer)
    main_ref = c << main_rect
    
    # Create the four upward fingers
    finger_width = 2.0
    finger_height = 4.0
    finger_spacing = (main_width - 4 * finger_width) / 5  # Equal spacing between fingers
    
    for i in range(4):
        finger_x = finger_spacing + i * (finger_width + finger_spacing)
        finger_y = main_height  # Start at top of main rectangle
        
        finger = gf.components.rectangle(size=(finger_width, finger_height), layer=layer)
        finger_ref = c << finger
        finger_ref.move((finger_x, finger_y))
    
    # Create the downward-pointing triangle tab
    # Triangle with base centered at bottom of main rectangle
    tab_base_width = 4.0
    tab_height = 2.0
    tab_x = main_width / 2.0 - tab_base_width / 2.0
    tab_y = 0.0  # Start at bottom of main rectangle
    
    triangle = gf.components.triangle(x=tab_base_width, y=tab_height, layer=layer)
    triangle_ref = c << triangle
    triangle_ref.move((tab_x, tab_y))
    # Rotate 180 degrees to point downward
    triangle_ref.rotate(180)
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")