import gdsfactory as gf

@gf.cell
def recreate_shape():
    c = gf.Component()
    layer = (1, 0)
    
    # Define the path for the entire shape
    # Start from bottom left, go clockwise around the shape
    
    # Calculate dimensions based on 25x10 footprint
    total_width = 25.0
    total_height = 10.0
    
    # Define prong parameters
    prong_width = 3.0
    prong_height = 3.0
    prong_spacing = 4.0  # center-to-center spacing
    
    # Calculate positions for prongs
    # 4 prongs with spacing, centered in the width
    total_prong_width = 4 * prong_width + 3 * prong_spacing
    start_x = (total_width - total_prong_width) / 2
    
    # Create path points for the entire shape
    path_points = []
    
    # Start at bottom left corner
    path_points.append((0, 0))
    
    # Go up left side
    path_points.append((0, total_height - prong_height))
    
    # First prong (bottom to top)
    path_points.append((start_x, total_height - prong_height))
    path_points.append((start_x, total_height))
    path_points.append((start_x + prong_width, total_height))
    path_points.append((start_x + prong_width, total_height - prong_height))
    
    # Space to next prong
    path_points.append((start_x + prong_width + prong_spacing, total_height - prong_height))
    
    # Second prong
    path_points.append((start_x + prong_width + prong_spacing, total_height))
    path_points.append((start_x + 2*prong_width + prong_spacing, total_height))
    path_points.append((start_x + 2*prong_width + prong_spacing, total_height - prong_height))
    
    # Space to next prong
    path_points.append((start_x + 2*prong_width + 2*prong_spacing, total_height - prong_height))
    
    # Third prong
    path_points.append((start_x + 2*prong_width + 2*prong_spacing, total_height))
    path_points.append((start_x + 3*prong_width + 2*prong_spacing, total_height))
    path_points.append((start_x + 3*prong_width + 2*prong_spacing, total_height - prong_height))
    
    # Space to next prong
    path_points.append((start_x + 3*prong_width + 3*prong_spacing, total_height - prong_height))
    
    # Fourth prong
    path_points.append((start_x + 3*prong_width + 3*prong_spacing, total_height))
    path_points.append((start_x + 4*prong_width + 3*prong_spacing, total_height))
    path_points.append((start_x + 4*prong_width + 3*prong_spacing, total_height - prong_height))
    
    # Go to bottom right corner
    path_points.append((total_width, total_height - prong_height))
    path_points.append((total_width, 0))
    
    # Add bottom point (triangle pointing down)
    # The triangle point should be centered at the bottom
    bottom_point_x = total_width / 2
    bottom_point_y = -2.0  # extend 2μm below the main body
    
    path_points.append((bottom_point_x + 1.0, 0))  # right side of triangle base
    path_points.append((bottom_point_x, bottom_point_y))  # bottom point
    path_points.append((bottom_point_x - 1.0, 0))  # left side of triangle base
    
    # Close the path back to start
    path_points.append((0, 0))
    
    # Create the path
    p = gf.Path()
    p.append(gf.path.straight(length=0))  # Start with a point
    
    # Add all the points to create the path
    for i in range(len(path_points) - 1):
        start_point = path_points[i]
        end_point = path_points[i + 1]
        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        segment_length = (dx**2 + dy**2)**0.5
        if segment_length > 0:
            p.append(gf.path.straight(length=segment_length))
    
    # Create a cross-section for extrusion
    xs = gf.cross_section.cross_section(width=1.0, layer=layer)
    
    # Extrude the path to create the shape
    # Since we want a solid shape, we need to create a polygon from the path
    # Alternative approach: use boolean operations to create the shape
    
    # Let's use a simpler approach with boolean operations
    c = gf.Component()
    
    # Create main rectangle
    main_rect = gf.components.rectangle(size=(total_width, total_height - prong_height), layer=layer)
    main_ref = c << main_rect
    main_ref.move((0, 0))
    
    # Create the four prongs as rectangles
    for i in range(4):
        prong_x = start_x + i * (prong_width + prong_spacing)
        prong_y = total_height - prong_height
        
        prong = gf.components.rectangle(size=(prong_width, prong_height), layer=layer)
        prong_ref = c << prong
        prong_ref.move((prong_x, prong_y))
    
    # Create the bottom triangle point
    triangle = gf.components.triangle(x=2.0, y=2.0, layer=layer)
    triangle_ref = c << triangle
    triangle_ref.move((total_width/2 - 1.0, -2.0))
    
    return c

# Create and save the device
device = recreate_shape()
device.write_gds("recreated_shape.gds")