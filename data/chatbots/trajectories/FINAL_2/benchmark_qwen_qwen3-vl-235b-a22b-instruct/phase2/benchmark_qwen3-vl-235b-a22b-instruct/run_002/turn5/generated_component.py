import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)
    
    # Define dimensions based on 25x10 footprint
    total_width = 25.0
    total_height = 10.0
    
    # Define prong parameters
    prong_base_width = 3.0  # width at the bottom (connected to main rectangle)
    prong_height = 3.0
    prong_spacing = 4.0  # center-to-center spacing
    
    # Calculate positions for prongs (centered in the width)
    total_prong_width = 4 * prong_base_width + 3 * prong_spacing
    start_x = (total_width - total_prong_width) / 2
    
    # Create the bottom triangle point
    triangle_base = 2.0
    triangle_height = 2.0
    
    # Create the entire shape as a single polygon using path system
    # Start from bottom left, go up, create prongs, go down, create bottom triangle, close
    
    # Create path for the polygon
    path_points = []
    
    # Start at bottom left corner
    path_points.append((0, 0))
    
    # Go up left side
    path_points.append((0, total_height - prong_height))
    
    # Create the four triangular prongs
    for i in range(4):
        prong_x = start_x + i * (prong_base_width + prong_spacing)
        
        # Bottom left of prong
        path_points.append((prong_x, total_height - prong_height))
        
        # Top point of prong (centered)
        path_points.append((prong_x + prong_base_width / 2, total_height))
        
        # Bottom right of prong
        path_points.append((prong_x + prong_base_width, total_height - prong_height))
    
    # Go down right side
    path_points.append((total_width, total_height - prong_height))
    path_points.append((total_width, 0))
    
    # Create bottom triangle point (centered)
    path_points.append((total_width / 2 + triangle_base / 2, 0))
    path_points.append((total_width / 2, -triangle_height))
    path_points.append((total_width / 2 - triangle_base / 2, 0))
    
    # Close the polygon
    path_points.append((0, 0))
    
    # Create a path from the points
    path = gf.Path(path_points)
    
    # Create a cross-section for the polygon
    # We'll use a very small width and then use boolean operations to fill it
    # But a better approach is to use the path to create a polygon directly
    
    # Since gf.components.polygon doesn't exist, let's use the path with a small width
    # and then use boolean operations to create the filled shape
    
    # Create a simple cross-section
    xs = gf.cross_section.cross_section(width=0.01, layer=layer)
    
    # Extrude the path
    extruded = gf.path.extrude(path, cross_section=xs)
    extruded_ref = c << extruded
    
    # The above approach might not work well for complex polygons
    # Let's use a different approach: create the shape with boolean operations
    
    # Clear the component and recreate using boolean operations
    c = gf.Component()
    
    # Create main rectangle
    main_rect = gf.components.rectangle(size=(total_width, total_height - prong_height), layer=layer)
    main_ref = c << main_rect
    main_ref.move((0, 0))
    
    # Create the four triangular prongs (pointing upward)
    for i in range(4):
        prong_x = start_x + i * (prong_base_width + prong_spacing)
        prong_y = total_height - prong_height
        
        # Create a triangle pointing upward
        # The triangle function creates a triangle with base along x-axis and point at (0, y)
        # We need to position it correctly
        triangle = gf.components.triangle(x=prong_base_width, y=prong_height, layer=layer)
        triangle_ref = c << triangle
        triangle_ref.move((prong_x, prong_y + prong_height))
        # Rotate 180 degrees to point upward
        triangle_ref.rotate(180)
        triangle_ref.movey(prong_y)
    
    # Create the bottom triangle point (downward pointing)
    bottom_triangle = gf.components.triangle(x=triangle_base, y=triangle_height, layer=layer)
    bottom_triangle_ref = c << bottom_triangle
    bottom_triangle_ref.move((total_width/2 - triangle_base/2, -triangle_height))
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")