import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)
    
    # Create the main body (25μm x 10μm)
    main_body = gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    main_ref = c << main_body
    
    # Create the four top extensions as trapezoids
    extension_width_top = 1.5
    extension_width_bottom = 0.5
    extension_height = 3.0
    extension_spacing = 5.0
    
    for i in range(4):
        x_pos = -12.5 + (i + 0.5) * extension_spacing
        
        # Create a trapezoid by creating two rectangles:
        # 1. A wider rectangle at the top
        # 2. A narrower rectangle below it
        top_rect = gf.components.rectangle(size=(extension_width_top, 0.5), layer=layer)
        top_ref = c << top_rect
        top_ref.move((x_pos, 5.0 + 0.25))
        
        # Create the narrower bottom part
        bottom_rect = gf.components.rectangle(size=(extension_width_bottom, extension_height - 0.5), layer=layer)
        bottom_ref = c << bottom_rect
        bottom_ref.move((x_pos, 5.0 - (extension_height - 0.5)/2 - 0.25))
    
    # Create the bottom triangular notch
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