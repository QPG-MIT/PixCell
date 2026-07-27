import gdsfactory as gf
import numpy as np

# Helper to calculate y-coordinates for elements (strips or gaps) centered on Y=0
def get_centered_y_coords(num_elements_count, element_w, gap_w):
    """
    Calculates Y-coordinates for the center of elements, symmetrically around Y=0.
    num_elements_count: total count of elements (e.g., num_lines + 1 for strips, or num_lines for gaps)
    element_w: width of a single element (strip_width or line_width)
    gap_w: width of the gap between elements
    """
    # Total height spanned by the elements and gaps
    total_span = num_elements_count * element_w + (num_elements_count - 1) * gap_w
    y_coords = []
    for i in range(num_elements_count):
        y_coords.append(-total_span / 2 + element_w / 2 + i * (element_w + gap_w))
    return y_coords

@gf.cell
def multi_lane_structure(
    total_width: float = 120.0,
    total_height: float = 4.0,
    length_central_straight: float = 60.0,
    num_lines_center: int = 4,  # Number of white lines in central part (implies 5 black strips)
    num_lines_curve: int = 5,   # Number of white lines in curved part (implies 6 black strips)
    strip_width: float = 0.45,  # Width of black material strips
    line_width: float = 0.2,    # Width of white gaps
    bend_radius: float = 10.0,  # Radius for smooth bends in paths (for overall outline and disappearing gaps)
    layer: gf.typings.LayerSpec = (1, 0),
) -> gf.Component:
    c = gf.Component("multi_lane_structure")

    # --- Calculate Dimensions ---
    # Height of the black block in the central region
    h_center_block_material = (num_lines_center + 1) * strip_width + num_lines_center * line_width
    # Height of the black block in the curved regions
    h_curve_block_material = (num_lines_curve + 1) * strip_width + num_lines_curve * line_width

    # X-coordinates for bend start/end
    x_central_half = length_central_straight / 2
    x_total_half = total_width / 2

    # Y-coordinates for the overall top/bottom boundaries (for the main black shape)
    y_total_top = total_height / 2
    y_total_bottom = -total_height / 2
    
    # Y-coordinates for the inner boundary of the central section (for the main black shape)
    y_central_top_material = h_center_block_material / 2
    y_central_bottom_material = -h_center_block_material / 2

    # --- 1. Construct the `main_black_shape` (Overall Black Outline) ---
    # Define waypoints for the perimeter of the entire black structure
    # Starting from bottom-left and going clockwise
    perimeter_waypoints = [
        (-x_total_half, y_total_bottom),              # A: Bottom-left outer corner
        (-x_central_half, y_central_bottom_material), # B: Bottom-left inner corner (of central section)
        (x_central_half, y_central_bottom_material),  # C: Bottom-right inner corner
        (x_total_half, y_total_bottom),               # D: Bottom-right outer corner
        (x_total_half, y_total_top),                  # E: Top-right outer corner
        (x_central_half, y_central_top_material),     # F: Top-right inner corner
        (-x_central_half, y_central_top_material),    # G: Top-left inner corner
        (-x_total_half, y_total_top),                 # H: Top-left outer corner
        (-x_total_half, y_total_bottom)               # A: Close the loop
    ]
    
    # Create a path from these waypoints, smoothing the corners.
    # `gf.path.smooth` ensures smooth transitions between straight and curved segments.
    black_outline_path = gf.path.smooth(points=perimeter_waypoints, radius=bend_radius)
    main_black_shape = c << black_outline_path.to_polygon(layer=layer)

    # --- 2. Create the `white_gaps_component` ---
    # Define a temporary component to hold all white gaps for boolean subtraction
    white_gaps_comp = gf.Component("white_gaps_for_subtraction")
    xs_gap = gf.cross_section.cross_section(width=line_width, layer=layer)

    # Y-centers for the white gaps in the central section (4 gaps)
    y_centers_gap_central = get_centered_y_coords(num_lines_center, line_width, strip_width)
    
    # Y-centers for the white gaps in the curved sections (5 gaps)
    y_centers_gap_curved = get_centered_y_coords(num_lines_curve, line_width, strip_width)
    
    # Calculate shift for central gaps to align with corresponding curved gaps (0,1,3,4)
    # Midpoint of the 4 central gaps
    midpoint_central_gaps = np.mean([y_centers_gap_central[0], y_centers_gap_central[1], y_centers_gap_central[2], y_centers_gap_central[3]])
    
    # Midpoint of the 4 corresponding curved gaps (0,1,3,4) from the `y_centers_gap_curved` list
    midpoint_curved_continuous_gaps = np.mean([y_centers_gap_curved[0], y_centers_gap_curved[1], y_centers_gap_curved[3], y_centers_gap_curved[4]])
    
    y_shift_gaps = midpoint_curved_continuous_gaps - midpoint_central_gaps
    y_centers_gap_central_shifted = [y + y_shift_gaps for y in y_centers_gap_central]
    
    # Iterate through all 5 possible white gaps based on the curved sections
    for i in range(num_lines_curve): # i = 0, 1, 2, 3, 4
        y_c_gap_curved_i = y_centers_gap_curved[i] # Y-center of the gap at the flared ends

        if i == 2: # This is the middle gap (index 2 of 5) that disappears in the central region
            # Create two bend_s components that curve towards Y=0 (disappearing point)
            
            # Left bend_s: starts at (-x_total_half, y_c_gap_curved_i), ends at (-x_central_half, 0)
            dy_disappear_left = 0 - y_c_gap_curved_i # Relative dy from start to end
            left_bend_disappear = gf.components.bend_s(size=(x_total_half - x_central_half, dy_disappear_left), cross_section=xs_gap)
            left_bend_disappear_ref = white_gaps_comp << left_bend_disappear
            # Connect the 'o1' port (which points left) to the starting point `(-x_total_half, y_c_gap_curved_i)` with orientation 180.
            left_bend_disappear_ref.connect("o1", gf.Port(name="in", center=(-x_total_half, y_c_gap_curved_i), width=line_width, orientation=180, layer=layer))
            
            # Right bend_s: starts at (x_central_half, 0), ends at (x_total_half, y_c_gap_curved_i)
            dy_disappear_right = y_c_gap_curved_i - 0 # Relative dy from start to end
            right_bend_disappear = gf.components.bend_s(size=(x_total_half - x_central_half, dy_disappear_right), cross_section=xs_gap)
            right_bend_disappear_ref = white_gaps_comp << right_bend_disappear
            # Connect the 'o1' port (which points left by default) to the starting point `(x_central_half, 0)` with orientation 0.
            # This requires rotating the bend_s component so its 'o1' port points right.
            right_bend_disappear_ref.connect("o1", gf.Port(name="in", center=(x_central_half, 0), width=line_width, orientation=0, layer=layer))

        else: # These are the 4 continuous gaps (indices 0,1,3,4 of y_centers_gap_curved)
            # Map to central gaps: `y_centers_gap_curved[0]` -> `y_centers_gap_central[0]`
            #                    `y_centers_gap_curved[1]` -> `y_centers_gap_central[1]`
            #                    `y_centers_gap_curved[3]` -> `y_centers_gap_central[2]`
            #                    `y_centers_gap_curved[4]` -> `y_centers_gap_central[3]`
            central_gap_map_idx = i
            if i > 1: # If i is 3 or 4, adjust index for y_centers_gap_central_shifted (as index 2 is skipped)
                central_gap_map_idx = i - 1 

            y_c_gap_central_j = y_centers_gap_central_shifted[central_gap_map_idx] # Y-center of this gap in the central section
            dy_gap_bend = y_c_gap_curved_i - y_c_gap_central_j # dy for the S-bend transition

            # Left S-bend
            left_bend_gap = gf.components.bend_s(size=(x_total_half - x_central_half, dy_gap_bend), cross_section=xs_gap)
            left_bend_gap_ref = white_gaps_comp << left_bend_gap
            left_bend_gap_ref.connect("o1", gf.Port(name="in", center=(-x_total_half, y_c_gap_curved_i), width=line_width, orientation=180, layer=layer))
            
            # Central straight section
            central_gap_straight = gf.components.straight(length=length_central_straight, cross_section=xs_gap)
            central_gap_straight_ref = white_gaps_comp << central_gap_straight
            central_gap_straight_ref.connect("o1", left_bend_gap_ref.ports["o2"])
            
            # Right S-bend
            right_bend_gap = gf.components.bend_s(size=(x_total_half - x_central_half, -dy_gap_bend), cross_section=xs_gap)
            right_bend_gap_ref = white_gaps_comp << right_bend_gap
            right_bend_gap_ref.connect("o1", central_gap_straight_ref.ports["o2"])

    # --- 3. Boolean Subtract ---
    final_device_component = gf.boolean(main_black_shape, white_gaps_comp, operation="not", layer=layer)
    c.add_ref(final_device_component)
    
    return c


if __name__ == "__main__":
    device = multi_lane_structure()
    device.show()
    print(f"Device Bounding Box: {device.bbox}")