import gdsfactory as gf

@gf.cell
def top_arm_design(
    W: float,
    center_bar_height: float,
    gap_vertical: float,
    outer_arm_width: float, 
    inner_arm_width: float, 
    radius_bend: float, # This is the centerline radius
    L_outer_taper_point: float,
    comb_x_offset_from_right: float,
    num_teeth: int,
    tooth_width: float,
    tooth_gap: float,
    tooth_height: float,
    layer: tuple = (1, 0),
) -> gf.Component:
    """
    Creates one of the U-shaped arms with comb teeth and a pointed taper.
    This design is for the top arm, positioned relative to a global (0,0) center.
    Mirroring this component will create the bottom arm correctly.
    """
    c = gf.Component("top_arm")
    
    # Define cross-sections for different parts
    # Set radius_min for xs_outer to allow for small bends
    xs_outer = gf.cross_section.cross_section(width=outer_arm_width, layer=layer, radius_min=radius_bend)
    xs_inner = gf.cross_section.cross_section(width=inner_arm_width, layer=layer) # Inner straight does not need radius_min unless it also forms a bend

    # Calculate y-coordinates for the centerlines of the paths
    # Bottom edge of the inner straight of the top arm (relative to y=0 center of device)
    y_inner_straight_bottom_edge = center_bar_height / 2 + gap_vertical
    y_inner_path_centerline = y_inner_straight_bottom_edge + inner_arm_width / 2
    
    # Centerline of the outer straight is 2*radius_bend above the inner straight's centerline.
    # This maintains the bend's centerline radius as the separation for the straight sections.
    y_outer_path_centerline = y_inner_path_centerline + 2 * radius_bend

    # 1. Main 180-degree Bend (left side of the arm)
    # Use bend_circular. By default, it creates a U-bend opening to the right.
    # Its ports are 'o1' (inner arc) and 'o2' (outer arc).
    bend_comp = gf.components.bend_circular(radius=radius_bend, angle=180, cross_section=xs_outer)
    bend_ref = c << bend_comp
    # Mirror across the Y-axis to make the U-bend open to the left.
    bend_ref.mirror(p1=(0, 0), p2=(0, 1)) 

    # After mirroring:
    # bend_ref.ports["o1"] is now the 'inner' port (bottom one), facing left (180 deg).
    # bend_ref.ports["o2"] is now the 'outer' port (top one), facing left (180 deg).

    # Position the bend. Its 'inner' port (o1) should align with the inner path centerline at x=-W/2.
    bend_ref.move(origin=bend_ref.ports["o1"].center, destination=(-W / 2, y_inner_path_centerline))

    # 2. Outer Straight Waveguide with Pointed Taper (right side)
    # This segment runs from the bend's 'o2' port (top, left-facing) towards the right end of the device (W/2).
    # The total horizontal extent of the outer arm from -W/2 to W/2 is W.
    # The taper occupies L_outer_taper_point at the end.
    outer_straight_len = W - L_outer_taper_point
    outer_straight_ref = c << gf.components.straight(length=outer_straight_len, cross_section=xs_outer)
    # Connect its left end ("o1") to the bend's 'o2' port.
    outer_straight_ref.connect("o1", bend_ref.ports["o2"])

    # Add the pointed taper to the right end of the outer straight.
    # Taper from outer_arm_width down to zero width.
    outer_taper_ref = c << gf.components.taper(length=L_outer_taper_point, width1=outer_arm_width, width2=0, layer=layer)
    # Connect taper's wide end ("o1") to the outer straight's right end ("o2").
    outer_taper_ref.connect("o1", outer_straight_ref.ports["o2"])

    # 3. Inner Straight Waveguide (from bend to blunt end on right, with comb)
    # This segment connects to the bend's 'o1' port (bottom, left-facing).
    # It needs to transition from the bend's width (outer_arm_width) to its own width (inner_arm_width).
    
    inner_taper_len = 0.5 # A chosen arbitrary length for this transition taper
    inner_taper_ref = c << gf.components.taper(length=inner_taper_len, width1=outer_arm_width, width2=inner_arm_width, layer=layer)
    # Connect its wide end ("o1") to the bend's 'o1' port.
    inner_taper_ref.connect("o1", bend_ref.ports["o1"])

    # Then the main inner straight segment.
    # Its total length will be W minus the taper length, as it spans from -W/2 to W/2.
    inner_straight_len = W - inner_taper_len
    inner_straight_ref = c << gf.components.straight(length=inner_straight_len, cross_section=xs_inner)
    # Connect its left end ("o1") to the taper's narrow end ("o2").
    inner_straight_ref.connect("o1", inner_taper_ref.ports["o2"])

    # 4. Comb Teeth on the Inner Straight Segment
    # The comb teeth are on the inner straight, extending downwards (for the top arm).
    # They are positioned towards the right end of the inner straight.
    
    # Calculate total horizontal length occupied by all teeth and their gaps.
    comb_active_length = num_teeth * tooth_width + (num_teeth - 1) * tooth_gap

    # Calculate the x-coordinate for the leftmost edge of the first tooth.
    # The rightmost edge of the last tooth should be at `W/2 - comb_x_offset_from_right`.
    comb_section_end_x = W/2 - comb_x_offset_from_right
    comb_section_start_x = comb_section_end_x - comb_active_length
    
    # Y-coordinate for the attachment point of the teeth (bottom edge of the inner straight).
    y_comb_attachment = y_inner_path_centerline - inner_arm_width / 2 

    # Add each tooth as a rectangle.
    for i in range(num_teeth):
        tooth_x_pos = comb_section_start_x + i * (tooth_width + tooth_gap) + tooth_width / 2
        tooth_y_pos = y_comb_attachment - tooth_height / 2
        tooth = c << gf.components.rectangle(size=(tooth_width, tooth_height), layer=layer, centered=True)
        tooth.move((tooth_x_pos, tooth_y_pos))
        
    return c


@gf.cell
def custom_device() -> gf.Component:
    """
    Assembles the complete device from the central bar and two U-shaped arms.
    """
    c = gf.Component("custom_device")

    # Overall device footprint dimensions from prompt
    W = 18.24  # Total width
    H = 0.7    # Total height

    # Derived Device component parameters based on H=0.7 and visual proportions:
    center_bar_height = 0.1  # Height of the central horizontal bar
    gap_vertical = 0.05      # Vertical gap between central bar and inner spine
    outer_arm_width = 0.15   # Width of the outer waveguide spine (wider)
    inner_arm_width = 0.05   # Width of the inner waveguide spine (narrower)
    radius_bend = 0.075      # Centerline radius of the bend (adjusted for H=0.7 to fit footprint)

    # Parameters for features
    L_outer_taper_point = 0.5        # Length of the pointed taper on the outer waveguide's right end
    comb_x_offset_from_right = 0.5   # Horizontal offset of the comb teeth from the right edge
    
    # Comb teeth parameters
    num_teeth = 26                   # Number of teeth in the comb
    tooth_width = 0.05               # Width of each individual tooth
    tooth_gap = 0.02                 # Horizontal spacing between teeth (adjusted to fit more teeth)
    tooth_height = 0.15              # Vertical extent of each tooth

    # 1. Central Bar
    # Placed centered at (0,0).
    c << gf.components.rectangle(size=(W, center_bar_height), layer=(1, 0), centered=True)

    # 2. Top Arm
    # Instantiate the 'top_arm_design' with the derived parameters.
    c << top_arm_design(
        W, center_bar_height, gap_vertical, 
        outer_arm_width, inner_arm_width, radius_bend, 
        L_outer_taper_point, comb_x_offset_from_right,
        num_teeth, tooth_width, tooth_gap, tooth_height,
        layer=(1, 0)
    )

    # 3. Bottom Arm
    # Create another instance of top_arm_design and mirror it across the x-axis.
    # This automatically flips its vertical position and makes the teeth point upwards.
    bottom_arm_ref = c << top_arm_design(
        W, center_bar_height, gap_vertical, 
        outer_arm_width, inner_arm_width, radius_bend, 
        L_outer_taper_point, comb_x_offset_from_right,
        num_teeth, tooth_width, tooth_gap, tooth_height,
        layer=(1, 0)
    )
    # Mirror across the x-axis (p1=(0,0), p2=(1,0) means horizontal mirror).
    bottom_arm_ref.mirror(p1=(0, 0), p2=(1, 0)) 

    return c

# Create the device and save the GDS file
if __name__ == "__main__":
    device = custom_device()
    device.write_gds("custom_device.gds")
    # To visualize the device, uncomment the line below and run in an environment
    # with a GDS viewer configured (e.g., KLayout, LVS).
    # device.show()