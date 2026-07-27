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
    finger_width = 2.0
    finger_height = 4.0
    total_finger_width = 4 * finger_width
    spacing = (main_width - total_finger_width) / 5
    
    for i in range(4):
        # Calculate position for each finger
        finger_x = spacing + i * (finger_width + spacing)
        
        # Create a trapezoid for the finger using a rectangle with a triangle on top
        # First, create the rectangular part
        rect_part = gf.components.rectangle(size=(finger_width, finger_height), layer=layer)
        rect_ref = c << rect_part
        rect_ref.move((finger_x, main_height))
        
        # The original image shows fingers that taper to a point, so let's add a triangle on top
        # But actually, looking at the original image, it appears the fingers are rectangular
        # with no taper. Let me reconsider based on the actual image.
    
    # Based on the original image, the fingers appear to be rectangular with no taper
    # Let's create them as simple rectangles
    
    # Recreate the fingers as simple rectangles
    for i in range(4):
        finger_x = spacing + i * (finger_width + spacing)
        finger = gf.components.rectangle(size=(finger_width, finger_height), layer=layer)
        finger_ref = c << finger
        finger_ref.move((finger_x, main_height))
    
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