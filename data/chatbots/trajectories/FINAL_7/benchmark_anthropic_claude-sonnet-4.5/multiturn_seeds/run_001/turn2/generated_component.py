import gdsfactory as gf
import numpy as np

@gf.cell
def chain_link_device():
    c = gf.Component()
    
    # Overall dimensions
    total_width = 5.5
    total_height = 3.0
    
    # Bar parameters
    bar_inner_gap = 0.8  # gap between the two bars at center
    bar_thickness = 0.6
    bar_start_x = 0.5
    bar_end_x = total_width
    
    # Divergence - bars spread apart as they go right
    upper_y_start = bar_inner_gap / 2
    lower_y_start = -bar_inner_gap / 2
    upper_y_end = total_height / 2 - 0.2
    lower_y_end = -total_height / 2 + 0.2
    
    # Create upper tapered bar
    upper_bar_points = [
        (bar_start_x, upper_y_start),
        (bar_end_x, upper_y_end),
        (bar_end_x, upper_y_end + bar_thickness),
        (bar_start_x, upper_y_start + bar_thickness),
    ]
    
    # Create lower tapered bar
    lower_bar_points = [
        (bar_start_x, lower_y_start - bar_thickness),
        (bar_end_x, lower_y_end - bar_thickness),
        (bar_end_x, lower_y_end),
        (bar_start_x, lower_y_start),
    ]
    
    # Create rounded left end connecting the bars
    round_center_x = 0.35
    n_points = 50
    
    # Create the rounded cap connecting both bars
    cap_points = []
    
    # Start from upper bar top edge at left
    cap_points.append((bar_start_x, upper_y_start + bar_thickness))
    cap_points.append((round_center_x, upper_y_start + bar_thickness))
    
    # Outer arc (top half)
    outer_radius = upper_y_start + bar_thickness
    for angle in np.linspace(np.pi/2, -np.pi/2, n_points):
        x = round_center_x + outer_radius * np.cos(angle)
        y = outer_radius * np.sin(angle)
        cap_points.append((x, y))
    
    # Bottom edge
    cap_points.append((round_center_x, lower_y_start - bar_thickness))
    cap_points.append((bar_start_x, lower_y_start - bar_thickness))
    
    # Inner arc (bottom to top)
    inner_radius = bar_inner_gap / 2
    for angle in np.linspace(-np.pi/2, np.pi/2, n_points):
        x = round_center_x + inner_radius * np.cos(angle)
        y = inner_radius * np.sin(angle)
        cap_points.append((x, y))
    
    # Add all main geometry
    c.add_polygon(upper_bar_points, layer=(1, 0))
    c.add_polygon(lower_bar_points, layer=(1, 0))
    c.add_polygon(cap_points, layer=(1, 0))
    
    # Create cutouts
    cutout_width = 1.5
    cutout_height = 0.35
    cutout_x_pos = 3.5
    
    # Calculate y position for upper cutout (interpolate along taper)
    progress = (cutout_x_pos - bar_start_x) / (bar_end_x - bar_start_x)
    upper_cutout_y = upper_y_start + bar_thickness/2 + (upper_y_end - upper_y_start) * progress
    
    # Calculate y position for lower cutout
    lower_cutout_y = lower_y_start - bar_thickness/2 + (lower_y_end - lower_y_start) * progress
    
    # Create main geometry component
    main_geom = gf.Component()
    main_geom.add_polygon(upper_bar_points, layer=(1, 0))
    main_geom.add_polygon(lower_bar_points, layer=(1, 0))
    main_geom.add_polygon(cap_points, layer=(1, 0))
    
    # Create cutout rectangles
    upper_cutout = gf.components.rectangle(
        size=(cutout_width, cutout_height),
        layer=(1, 0),
        centered=True
    )
    upper_cutout_moved = upper_cutout.copy()
    upper_cutout_moved.move((cutout_x_pos, upper_cutout_y))
    
    lower_cutout = gf.components.rectangle(
        size=(cutout_width, cutout_height),
        layer=(1, 0),
        centered=True
    )
    lower_cutout_moved = lower_cutout.copy()
    lower_cutout_moved.move((cutout_x_pos, lower_cutout_y))
    
    # Perform boolean operations
    temp = gf.boolean(main_geom, upper_cutout_moved, operation="not", layer=(1, 0))
    result = gf.boolean(temp, lower_cutout_moved, operation="not", layer=(1, 0))
    
    return result

# Create and save the device
device = chain_link_device()
device.write_gds("chain_link_device.gds")
print("Chain link device GDS created successfully!")