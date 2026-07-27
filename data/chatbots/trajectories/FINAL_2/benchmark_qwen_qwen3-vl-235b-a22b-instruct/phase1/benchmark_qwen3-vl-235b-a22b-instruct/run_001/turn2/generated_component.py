import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    
    # Define layer
    layer = (1, 0)
    
    # Create the main body (25μm x 10μm)
    main_body = gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    main_ref = c << main_body
    
    # Create the four top extensions
    # Each extension will be a trapezoid that connects to the main body
    extension_width = 1.5
    extension_height = 3.0
    extension_spacing = 5.0
    
    for i in range(4):
        # Create a trapezoid for each extension
        # We'll create a rectangle and then use boolean operations or create a polygon
        # But since we can't use raw polygons, let's create a rectangle and position it
        extension = gf.components.rectangle(size=(extension_width, extension_height), layer=layer)
        extension_ref = c << extension
        
        # Position at top, with spacing
        x_pos = -12.5 + (i + 0.5) * extension_spacing
        y_pos = 5.0 + extension_height / 2
        extension_ref.move((x_pos, y_pos))
    
    # Create the bottom triangular notch
    # We can create a triangle using the triangle component
    notch_base = 2.0
    notch_height = 2.0
    
    # Create a triangle pointing downward
    triangle = gf.components.triangle(x=notch_base, y=notch_height, layer=layer)
    triangle_ref = c << triangle
    
    # Position at bottom center, pointing downward
    triangle_ref.move((0, -5.0 - notch_height / 2))
    triangle_ref.rotate(180)  # Rotate to point downward
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")