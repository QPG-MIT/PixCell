import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)  # Default layer
    
    # Main rectangular body
    main_width = 25.0
    main_height = 8.0
    main_rect = gf.components.rectangle(size=(main_width, main_height), layer=layer)
    main_ref = c << main_rect
    
    # Create the four upward tapered fingers
    finger_base_width = 2.0
    finger_height = 4.0
    total_finger_width = 4 * finger_base_width
    spacing = (main_width - total_finger_width) / 5
    
    for i in range(4):
        # Calculate position for each finger
        finger_x = spacing + i * (finger_base_width + spacing)
        
        # Create a triangle for the tapered finger
        # The triangle function creates a right triangle with base x and height y
        # We need to position it so the base is at the bottom and it points upward
        triangle = gf.components.triangle(x=finger_base_width, y=finger_height, layer=layer)
        triangle_ref = c << triangle
        triangle_ref.move((finger_x, main_height))
    
    # Create the downward-pointing triangle tab
    tab_base_width = 2.0
    tab_height = 2.0
    tab_x = main_width / 2.0 - tab_base_width / 2.0
    tab_y = 0.0
    
    triangle = gf.components.triangle(x=tab_base_width, y=tab_height, layer=layer)
    triangle_ref = c << triangle
    triangle_ref.move((tab_x, tab_y))
    triangle_ref.rotate(180)  # Point downward
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape_final.gds")