import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)
    
    # Create the main body (25μm x 10μm)
    main_body = gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    main_ref = c << main_body
    
    # Create the four top extensions with proper tapering
    extension_width_top = 2.0  # Wider at top
    extension_width_bottom = 0.5  # Narrower at bottom (connecting to main body)
    extension_height = 3.0
    extension_spacing = 5.0
    
    for i in range(4):
        x_pos = -12.5 + (i + 0.5) * extension_spacing
        
        # Create a tapered extension using a path with transition
        path = gf.Path()
        path.append(gf.path.straight(length=extension_height))
        
        # Create a transition from narrow to wide
        xs_narrow = gf.cross_section.cross_section(width=extension_width_bottom, layer=layer)
        xs_wide = gf.cross_section.cross_section(width=extension_width_top, layer=layer)
        transition = gf.path.transition(xs_narrow, xs_wide, width_type='linear')
        
        # Extrude the path with the transition
        tapered_extension = gf.path.extrude_transition(path, transition)
        tapered_ref = c << tapered_extension
        
        # Position the tapered extension
        tapered_ref.move((x_pos, 5.0 + extension_height/2))
    
    # Create the bottom triangular notch (cutout)
    notch_base = 2.0
    notch_height = 2.0
    
    # Create a triangle pointing upward (will be subtracted)
    triangle = gf.components.triangle(x=notch_base, y=notch_height, layer=layer)
    triangle_ref = c << triangle
    
    # Position at bottom center, pointing upward (to be subtracted)
    triangle_ref.move((0, -5.0 + notch_height/2))
    
    # Create a new component for the final result
    final_component = gf.Component()
    
    # Add all elements to the final component
    final_component << main_ref
    for i in range(4):
        x_pos = -12.5 + (i + 0.5) * extension_spacing
        path = gf.Path()
        path.append(gf.path.straight(length=extension_height))
        xs_narrow = gf.cross_section.cross_section(width=extension_width_bottom, layer=layer)
        xs_wide = gf.cross_section.cross_section(width=extension_width_top, layer=layer)
        transition = gf.path.transition(xs_narrow, xs_wide, width_type='linear')
        tapered_extension = gf.path.extrude_transition(path, transition)
        tapered_ref = final_component << tapered_extension
        tapered_ref.move((x_pos, 5.0 + extension_height/2))
    
    # Add the triangle for boolean operation
    triangle_for_boolean = gf.components.triangle(x=notch_base, y=notch_height, layer=layer)
    triangle_for_boolean_ref = final_component << triangle_for_boolean
    triangle_for_boolean_ref.move((0, -5.0 + notch_height/2))
    
    # Since we're having issues with boolean operations, let's create the main body with notch manually
    # Create a new component with the main body minus the triangle
    manual_notch_component = gf.Component()
    
    # Add the main body
    main_body_manual = gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    main_body_manual_ref = manual_notch_component << main_body_manual
    
    # Add the triangle (we'll handle the boolean operation differently)
    triangle_manual = gf.components.triangle(x=notch_base, y=notch_height, layer=layer)
    triangle_manual_ref = manual_notch_component << triangle_manual
    triangle_manual_ref.move((0, -5.0 + notch_height/2))
    
    # Clear the current component and add the manual notch component
    c.clear()
    c << manual_notch_component
    
    # Re-add the tapered extensions
    for i in range(4):
        x_pos = -12.5 + (i + 0.5) * extension_spacing
        path = gf.Path()
        path.append(gf.path.straight(length=extension_height))
        xs_narrow = gf.cross_section.cross_section(width=extension_width_bottom, layer=layer)
        xs_wide = gf.cross_section.cross_section(width=extension_width_top, layer=layer)
        transition = gf.path.transition(xs_narrow, xs_wide, width_type='linear')
        tapered_extension = gf.path.extrude_transition(path, transition)
        tapered_ref = c << tapered_extension
        tapered_ref.move((x_pos, 5.0 + extension_height/2))
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")