import gdsfactory as gf

@gf.cell
def custom_splitter():
    """
    Recreates the geometry from the provided image using GDSFactory parametric functions.

    The device consists of three input waveguides on the left. The middle one
    is a straight segment, while the top and bottom ones taper and curve
    inwards to merge into a single wider output waveguide on the right.
    """
    c = gf.Component("custom_splitter")

    # --- Device Parameters ---
    L_total = 40.0  # Total length of the device (x-dimension of footprint)
    total_height = 1.7  # Total height of the device (y-dimension of footprint)
    initial_waveguide_width = 0.2  # Width of the input straight waveguides

    # --- Derived Parameters ---
    # The device is centered vertically at y=0.
    # The top-most edge is at y = total_height / 2 = 0.85
    # The bottom-most edge is at y = -total_height / 2 = -0.85

    # Initial y-coordinate for the centerline of the outer waveguides
    # This ensures the outermost edge of the initial waveguide is at total_height/2
    y_start_outer = total_height / 2 - initial_waveguide_width / 2

    # The top and bottom arms merge to form a single output waveguide
    # whose width is `total_height` (1.7 um).
    # Each arm contributes half of this width at the merge point.
    final_arm_width = total_height / 2

    # The centerline of the top arm ends at the center of the top half of the output waveguide.
    # The centerline of the bottom arm ends at the center of the bottom half of the output waveguide.
    y_final_center_arm = total_height / 4

    # Define the lengths of different sections along the x-axis
    L_straight_input = 10.0  # Length of the initial straight waveguide segment
    L_output_section = 10.0  # Length of the final straight output waveguide segment
    # The middle section is where the taper and bend occur
    L_middle_section = L_total - L_straight_input - L_output_section

    # The middle (inner) waveguide's length, visually it ends near the center of the device
    L_inner_waveguide = L_straight_input + L_middle_section / 2

    # --- Cross-section Definitions ---
    # All geometry is placed on layer (1, 0)
    xs_start = gf.cross_section.cross_section(width=initial_waveguide_width, layer=(1, 0))
    xs_end_arm = gf.cross_section.cross_section(width=final_arm_width, layer=(1, 0))

    # Define a smooth width transition for the outer arms
    # 'sine' type transition creates a smoothly varying width
    transition = gf.path.transition(xs_start, xs_end_arm, width_type='sine')

    # --- Bezier Curve Control Point Calculations ---
    # The bezier curve connects the initial straight part to the final straight part.
    # It starts at x_bend_start and ends at x_bend_end.
    x_bend_start = L_straight_input
    x_bend_end = L_total - L_output_section  # The x-coordinate where the bend/taper ends

    # These intermediate control points help ensure the bezier curve starts and ends
    # with a horizontal tangent, connecting smoothly to the straight segments.
    bezier_span_x = x_bend_end - x_bend_start
    cx1 = x_bend_start + bezier_span_x / 3
    cx2 = x_bend_start + 2 * bezier_span_x / 3

    # --- 1. Middle Waveguide ---
    # A simple straight waveguide, centered at y=0.
    # This creates a Path object that is a single straight segment.
    p_mid = gf.path.straight(length=L_inner_waveguide)
    c_mid = gf.path.extrude(p_mid, cross_section=xs_start)
    ref_mid = c << c_mid
    ref_mid.movey(0)  # Ensure it's centered vertically

    # --- 2. Top Arm ---
    # Create the path for the centerline of the top arm, starting at the initial point.
    path_top_center = gf.Path([(0, y_start_outer)])
    
    # Append segments using the Path object's methods directly.
    path_top_center.straight(L_straight_input)
    
    # FIX: Call .bezier() method directly on the path object, not gf.path.bezier()
    path_top_center.bezier(control_points=[
        (x_bend_start, y_start_outer),      # Start of bezier (matches end of straight input)
        (cx1, y_start_outer),               # Control point for horizontal tangent at start
        (cx2, y_final_center_arm),          # Control point to guide towards final y-position and horizontal tangent
        (x_bend_end, y_final_center_arm)    # End of bezier (matches start of straight output)
    ])
    path_top_center.straight(L_output_section)  # Append final straight segment

    # Extrude the path with the defined width transition
    comp_top_arm = gf.path.extrude_transition(path_top_center, transition)
    ref_top = c << comp_top_arm

    # --- 3. Bottom Arm (Symmetric to Top Arm) ---
    # Create the path for the centerline of the bottom arm, mirrored vertically
    path_bottom_center = gf.Path([(0, -y_start_outer)])
    path_bottom_center.straight(L_straight_input)

    # FIX: Call .bezier() method directly on the path object, not gf.path.bezier()
    path_bottom_center.bezier(control_points=[
        (x_bend_start, -y_start_outer),
        (cx1, -y_start_outer),
        (cx2, -y_final_center_arm),
        (x_bend_end, -y_final_center_arm)
    ])
    path_bottom_center.straight(L_output_section)

    comp_bottom_arm = gf.path.extrude_transition(path_bottom_center, transition)
    ref_bottom = c << comp_bottom_arm

    # --- Merge Outer Arms with Boolean OR ---
    # The image shows the top and bottom arms merging into a single, continuous structure
    # at the output. A boolean OR operation achieves this, creating a single polygon
    # from the overlapping parts. The current design ensures the arms meet perfectly at y=0.
    merged_arms = gf.boolean(ref_top, ref_bottom, operation="or", layer=(1, 0))
    c << merged_arms
    
    # Remove the individual arm references, as they are now combined into 'merged_arms'
    c.remove_references([ref_top, ref_bottom])

    # The final device footprint (40.0 um, 1.7 um) is naturally achieved by these dimensions.
    return c

# Create the device component
device = custom_splitter()

# Write the GDS file
device.write_gds("custom_splitter.gds")

# Optional: Display the component (requires KLayout or similar viewer setup)
# gf.show(device)