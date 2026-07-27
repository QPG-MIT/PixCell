import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)  # Default layer
    
    # Main rectangular body (footprint is 25x10, so this will be most of it)
    # I'll make it slightly smaller to accommodate the prongs and point
    main_width = 24.0
    main_height = 8.0
    main_rect = gf.components.rectangle(size=(main_width, main_height), layer=layer)
    main_ref = c << main_rect
    main_ref.move((0, 0))  # Position at origin
    
    # Create the four vertical prongs
    prong_width = 2.0
    prong_height = 4.0
    prong_spacing = 5.0  # spacing between prong centers
    
    # Position the prongs along the top edge of the main rectangle
    # First prong at x = 1.5 (leaving 1.0 margin from left edge)
    for i in range(4):
        prong_x = 1.5 + i * prong_spacing
        prong_y = main_height  # Start at top of main rectangle
        
        prong = gf.components.rectangle(size=(prong_width, prong_height), layer=layer)
        prong_ref = c << prong
        prong_ref.move((prong_x, prong_y))
    
    # Create the bottom point (triangle)
    # Triangle pointing downward from bottom center
    triangle_base = 4.0
    triangle_height = 2.0
    
    triangle = gf.components.triangle(x=triangle_base, y=triangle_height, layer=layer)
    triangle_ref = c << triangle
    # Position at bottom center of main rectangle
    triangle_ref.move((main_width/2 - triangle_base/2, -triangle_height))
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")