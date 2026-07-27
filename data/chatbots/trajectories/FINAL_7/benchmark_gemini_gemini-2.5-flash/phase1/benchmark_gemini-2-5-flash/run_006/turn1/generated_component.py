import gdsfactory as gf
import math

@gf.cell
def my_device():
    c = gf.Component("oval_device")
    layer = (1, 0) # Default layer for the device geometry

    # Device footprint dimensions
    x_total_span = 3.0 # microns
    y_total_span = 5.5 # microns

    # Radii for the outer ellipse
    x_radius = x_total_span / 2 # 1.5 um
    y_radius = y_total_span / 2 # 2.75 um

    # Parameters for central horizontal bars and their holes
    bar_length_half = 1.0  # Half length of the main straight section of the bar (total length 2.0 um)
    bar_width = 0.5        # Height of the central bars
    central_gap_y = 0.5    # Vertical spacing between the top and bottom bars
    
    # Y-coordinate of the center of the top bar. Bottom bar will be at -y_center_top_bar.
    y_center_top_bar = central_gap_y / 2 + bar_width / 2

    hole_size = 0.3        # Side length of the square holes
    hole_spacing = 0.7     # Center-to-center distance between the two holes in a bar

    # Parameters for the connecting arms
    arm_start_width = bar_width  # Width of the arm where it connects to the central bar
    arm_end_width = 0.8          # Width of the arm where it connects to the outer ellipse
    arm_path_smooth_radius = 0.2 # Radius for smoothing the path segments in gf.path.smooth

    # List to collect all individual black geometric components
    all_black_parts = []

    # 1. Create the Outer Ellipse (as the overall bounding shape)
    outer_ellipse_comp = gf.components.ellipse(radii=(x_radius, y_radius), layer=layer)
    all_black_parts.append(outer_ellipse_comp)

    # 2. Create the Central Horizontal Bars with internal holes
    # Create the base rectangular body and hole template once.
    # We will use .copy() on these templates before moving and boolean operations.
    base_bar_body_template = gf.components.rectangle(size=(bar_length_half * 2, bar_width), layer=layer, centered=True)
    hole_template = gf.components.rectangle(size=(hole_size, hole_size), layer=layer, centered=True)

    # Top bar:
    bar_rect_body_top = base_bar_body_template.copy().movey(y_center_top_bar)
    hole_pos_x_offset = hole_spacing / 2
    hole1_top = hole_template.copy().move((hole_pos_x_offset, y_center_top_bar))
    hole2_top = hole_template.copy().move((-hole_pos_x_offset, y_center_top_bar))

    bar_with_holes_top_comp = gf.boolean(
        bar_rect_body_top,
        [hole1_top, hole2_top], # Pass list of holes to subtract
        operation="not",
        layer=layer
    )
    all_black_parts.append(bar_with_holes_top_comp)

    # Bottom bar:
    bar_rect_body_bottom = base_bar_body_template.copy().movey(-y_center_top_bar)
    hole3_bottom = hole_template.copy().move((hole_pos_x_offset, -y_center_top_bar))
    hole4_bottom = hole_template.copy().move((-hole_pos_x_offset, -y_center_top_bar))

    bar_with_holes_bottom_comp = gf.boolean(
        bar_rect_body_bottom,
        [hole3_bottom, hole4_bottom], # Pass list of holes to subtract
        operation="not",
        layer=layer
    )
    all_black_parts.append(bar_with_holes_bottom_comp)

    # 3. Create the four Connecting Arms
    
    # Define cross-sections for the arm's width transition
    xs_arm_start = gf.cross_section.cross_section(width=arm_start_width, layer=layer)
    xs_arm_end = gf.cross_section.cross_section(width=arm_end_width, layer=layer)
    
    # Create a linear transition object for the arm's width
    arm_transition = gf.path.transition(xs1=xs_arm_start, xs2=xs_arm_end, width_type='linear')

    # Calculate the end x, y coordinates for the arm's centerline.
    arm_path_end_x = x_radius - (arm_end_width / 2) 
    arm_path_end_y = y_radius * math.sqrt(1 - (arm_path_end_x / x_radius)**2) if x_radius != 0 else y_radius

    # Top-Right Arm
    p_start_tr = (bar_length_half, y_center_top_bar)
    p_waypoint1_tr = (bar_length_half + 0.2, y_center_top_bar + 0.1) 
    p_waypoint2_tr = (bar_length_half + 0.25, y_center_top_bar + 0.6)
    p_end_tr = (arm_path_end_x, arm_path_end_y)
    arm_tr_path = gf.path.smooth(points=[p_start_tr, p_waypoint1_tr, p_waypoint2_tr, p_end_tr], radius=arm_path_smooth_radius)
    arm_tr_comp = gf.path.extrude_transition(arm_tr_path, arm_transition)
    all_black_parts.append(arm_tr_comp)

    # Top-Left Arm
    p_start_tl = (-bar_length_half, y_center_top_bar)
    p_waypoint1_tl = (-(bar_length_half + 0.2), y_center_top_bar + 0.1)
    p_waypoint2_tl = (-(bar_length_half + 0.25), y_center_top_bar + 0.6)
    p_end_tl = (-arm_path_end_x, arm_path_end_y)
    arm_tl_path = gf.path.smooth(points=[p_start_tl, p_waypoint1_tl, p_waypoint2_tl, p_end_tl], radius=arm_path_smooth_radius)
    arm_tl_comp = gf.path.extrude_transition(arm_tl_path, arm_transition)
    all_black_parts.append(arm_tl_comp)

    # Bottom-Right Arm
    p_start_br = (bar_length_half, -y_center_top_bar)
    p_waypoint1_br = (bar_length_half + 0.2, -(y_center_top_bar + 0.1))
    p_waypoint2_br = (bar_length_half + 0.25, -(y_center_top_bar + 0.6))
    p_end_br = (arm_path_end_x, -arm_path_end_y)
    arm_br_path = gf.path.smooth(points=[p_start_br, p_waypoint1_br, p_waypoint2_br, p_end_br], radius=arm_path_smooth_radius)
    arm_br_comp = gf.path.extrude_transition(arm_br_path, arm_transition)
    all_black_parts.append(arm_br_comp)

    # Bottom-Left Arm
    p_start_bl = (-bar_length_half, -y_center_top_bar)
    p_waypoint1_bl = (-(bar_length_half + 0.2), -(y_center_top_bar + 0.1))
    p_waypoint2_bl = (-(bar_length_half + 0.25), -(y_center_top_bar + 0.6))
    p_end_bl = (-arm_path_end_x, -arm_path_end_y)
    arm_bl_path = gf.path.smooth(points=[p_start_bl, p_waypoint1_bl, p_waypoint2_bl, p_end_bl], radius=arm_path_smooth_radius)
    arm_bl_comp = gf.path.extrude_transition(arm_bl_path, arm_transition)
    all_black_parts.append(arm_bl_comp)

    # 4. Combine all collected black parts into a single final geometry iteratively
    # Start with the first component in the list.
    final_combined_shape = all_black_parts[0]

    # Iterate through the rest of the components and merge them one by one.
    for i in range(1, len(all_black_parts)):
        final_combined_shape = gf.boolean(
            final_combined_shape,  # A is the current combined shape
            all_black_parts[i],    # B is the next single component to merge
            operation="or",
            layer=layer
        )
    
    # Add the resulting combined shape as a reference to the main component 'c'.
    c.add_ref(final_combined_shape)

    return c

# To visualize the generated GDSFactory component:
if __name__ == "__main__":
    device = my_device()
    device.show() # Opens the component in a GDS viewer (requires KLayout or similar)
    # device.write_gds("oval_device.gds") # Saves the component to a GDSII file