import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)
    
    # Define dimensions based on 25x10 footprint
    total_width = 25.0
    total_height = 10.0
    
    # Main rectangle base
    base_height = 8.0  # Height of the main rectangle
    base_width = total_width
    base = gf.components.rectangle(size=(base_width, base_height), layer=layer, centered=False)
    
    # Create the bottom triangular point
    triangle_width = 2.0
    triangle_height = 2.0
    bottom_triangle = gf.Component()
    # Create the triangle geometry pointing downward
    points = [(0, 0), (triangle_width, 0), (triangle_width/2, -triangle_height)]
    bottom_triangle.add_polygon(points, layer=layer)
    # Position the triangle at the bottom center of the base
    bottom_triangle.move((total_width/2 - triangle_width/2, base_height))
    
    # Add the main rectangle and bottom triangle to the component
    c.add_ref(base)
    c.add_ref(bottom_triangle)
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")