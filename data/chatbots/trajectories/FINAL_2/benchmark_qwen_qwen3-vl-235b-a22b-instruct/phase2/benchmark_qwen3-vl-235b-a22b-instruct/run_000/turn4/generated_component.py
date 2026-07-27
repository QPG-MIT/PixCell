import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)
    
    # Define dimensions based on 25x10 footprint
    total_width = 25.0
    total_height = 10.0
    
    # Main rectangle base
    base_height = 8.0
    base_width = total_width
    base = gf.components.rectangle(size=(base_width, base_height), layer=layer, centered=False)
    
    # Calculate positions for the four inverted triangular notches
    notch_width = 2.0  # Width of each triangular notch at the top
    notch_height = 2.0  # Height of each triangular notch
    spacing = (total_width - 4 * notch_width) / 5  # Equal spacing between notches
    
    # Create a component to hold all notches
    notch_component = gf.Component()
    
    # Create and position the four inverted triangular notches
    for i in range(4):
        x_pos = spacing + i * (notch_width + spacing)
        
        # Create a new triangle component
        triangle = gf.Component()
        # Create the triangle geometry directly
        points = [(0, 0), (notch_width, 0), (notch_width/2, notch_height)]
        triangle.add_polygon(points, layer=layer)
        
        # Mirror to point downward
        triangle.mirror()
        
        # Position the notch at the top of the base
        triangle.move((x_pos + notch_width/2, base_height))
        
        # Add to notch component
        notch_component.add_ref(triangle)
    
    # Create the bottom triangular point
    triangle_width = 2.0
    triangle_height = 2.0
    bottom_triangle = gf.Component()
    # Create the triangle geometry directly
    points = [(0, 0), (triangle_width, 0), (triangle_width/2, triangle_height)]
    bottom_triangle.add_polygon(points, layer=layer)
    bottom_triangle.move((total_width/2 - triangle_width/2, -triangle_height))
    
    # Perform boolean operations
    # First, create the main shape by subtracting notches from base
    main_shape = gf.boolean(base, notch_component, operation="not", layer=layer)
    
    # Add the main shape and bottom triangle to the component
    c.add_ref(main_shape)
    c.add_ref(bottom_triangle)
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")