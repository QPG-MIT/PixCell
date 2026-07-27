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
    finger_top_width = 0.5  # Narrower at the top
    finger_height = 4.0
    total_finger_width = 4 * finger_base_width
    spacing = (main_width - total_finger_width) / 5
    
    for i in range(4):
        # Calculate position for each finger
        finger_x = spacing + i * (finger_base_width + spacing)
        
        # Create a trapezoid for the tapered finger
        # We'll create this using a path with varying width
        path = gf.Path()
        path.append(gf.path.straight(length=finger_height))
        
        # Create a cross-section that tapers from base to top
        xs_base = gf.cross_section.cross_section(width=finger_base_width, layer=layer)
        xs_top = gf.cross_section.cross_section(width=finger_top_width, layer=layer)
        transition = gf.path.transition(xs_base, xs_top, width_type='linear')
        
        # Extrude the path with the transition
        finger = gf.path.extrude_transition(path, transition)
        finger_ref = c << finger
        finger_ref.move((finger_x + finger_base_width/2 - finger_top_width/2, main_height))
    
    # Create the downward-pointing trapezoid tab
    tab_base_width = 2.0
    tab_top_width = 0.5  # Narrower at the bottom (since it's pointing down)
    tab_height = 2.0
    tab_x = main_width / 2.0 - tab_base_width / 2.0
    tab_y = 0.0
    
    # Create a trapezoid for the tab
    path = gf.Path()
    path.append(gf.path.straight(length=tab_height))
    
    # Create a cross-section that tapers from base to top
    xs_base = gf.cross_section.cross_section(width=tab_base_width, layer=layer)
    xs_top = gf.cross_section.cross_section(width=tab_top_width, layer=layer)
    transition = gf.path.transition(xs_base, xs_top, width_type='linear')
    
    # Extrude the path with the transition
    tab = gf.path.extrude_transition(path, transition)
    tab_ref = c << tab
    tab_ref.move((tab_x + tab_base_width/2 - tab_top_width/2, tab_y))
    tab_ref.rotate(180)  # Point downward
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape_final.gds")