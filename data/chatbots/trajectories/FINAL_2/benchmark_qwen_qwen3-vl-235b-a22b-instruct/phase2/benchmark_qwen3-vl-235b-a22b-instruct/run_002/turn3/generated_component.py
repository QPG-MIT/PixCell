import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)
    
    # Define dimensions based on 25x10 footprint
    total_width = 25.0
    total_height = 10.0
    
    # Define prong parameters
    prong_width = 3.0
    prong_height = 3.0
    prong_spacing = 4.0  # center-to-center spacing
    
    # Calculate positions for prongs (centered in the width)
    total_prong_width = 4 * prong_width + 3 * prong_spacing
    start_x = (total_width - total_prong_width) / 2
    
    # Create main rectangle (excluding the prong height)
    main_height = total_height - prong_height
    main_rect = gf.components.rectangle(size=(total_width, main_height), layer=layer)
    main_ref = c << main_rect
    main_ref.move((0, 0))
    
    # Create the four prongs as rectangles extending upward
    for i in range(4):
        prong_x = start_x + i * (prong_width + prong_spacing)
        prong_y = main_height  # Start at the top of the main rectangle
        
        prong = gf.components.rectangle(size=(prong_width, prong_height), layer=layer)
        prong_ref = c << prong
        prong_ref.move((prong_x, prong_y))
    
    # Create the bottom triangle point (downward pointing)
    # The triangle should be centered at the bottom of the main rectangle
    triangle_base = 2.0
    triangle_height = 2.0
    
    # Create a triangle pointing downward
    triangle = gf.components.triangle(x=triangle_base, y=triangle_height, layer=layer)
    triangle_ref = c << triangle
    
    # Position the triangle at the bottom center
    # The triangle function creates a triangle with base along x-axis and point at (0, y)
    # We need to flip it to point downward
    triangle_ref.move((total_width/2 - triangle_base/2, -triangle_height))
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")