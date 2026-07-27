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
    
    # Create the four upward rectangular fingers (not tapered)
    finger_width = 2.0
    finger_height = 4.0
    total_finger_width = 4 * finger_width
    spacing = (main_width - total_finger_width) / 5
    
    for i in range(4):
        # Calculate position for each finger
        finger_x = spacing + i * (finger_width + spacing)
        
        # Create a simple rectangle for each finger
        finger_rect = gf.components.rectangle(size=(finger_width, finger_height), layer=layer)
        finger_ref = c << finger_rect
        finger_ref.move((finger_x, main_height))
    
    # Create the downward-pointing triangular tab using add_polygon
    tab_base_width = 2.0
    tab_height = 2.0
    tab_x = main_width / 2.0 - tab_base_width / 2.0
    tab_y = 0.0
    
    # Define vertices of the downward-pointing triangle
    points = [
        (tab_x, tab_y),                          # bottom-left
        (tab_x + tab_base_width, tab_y),         # bottom-right
        (tab_x + tab_base_width / 2, tab_y - tab_height)  # tip pointing down
    ]
    
    # Add the triangle directly as a polygon
    c.add_polygon(points, layer=layer)
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape_final.gds")