import gdsfactory as gf

@gf.cell
def top_arm_design(
    W: float,
    center_bar_height: float,
    gap_vertical: float,
    spine_width: float,
    radius_bend: float,
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
    
    # Define cross-section with updated spine_width and radius_min to allow small bends
    xs = gf.cross_section.cross_section(width=spine_width, layer=layer, radius_min=radius_bend)

    # Calculate y-coordinates for the centerlines of the paths
    # Center of the central bar is y=0. Top edge is center_bar_height/2.
    # Inner straight's centerline is above this, separated by gap_vertical + half spine_width.
    y_inner_path = center_bar_height / 2 + gap_vertical + spine_width / 2
    # Outer straight's centerline is above inner straight's centerline by 2 * radius_bend.
    y_outer_path = y_inner_path + 2 * radius_bend 

    # 1. Main 180-degree Bend (left side of the arm)
    # bend_circular(angle=180) by default has 'o1' (inner port) at (0,0) facing 0 deg, 
    # and 'o2' (outer port) at (0, 2*radius) facing 0 deg.
    bend_ref = c << gf.components.bend_circular(radius=radius_bend, angle=180, cross_section=xs)
    
    # Move the bend so its 'o1' port's center aligns with the leftmost device edge (x=-W/2)
    # and the calculated y_inner_path.
    bend_ref.move(origin=bend_ref.ports["o1"].center, destination=(-W / 2, y_inner_path))
    
    # 2. Outer Straight Waveguide with Pointed Taper (right side)
    # This segment runs from the bend's outer port (o2) to the right edge with a taper.
    # The total horizontal extent of the outer waveguide (including taper) is W.
    outer_straight_len = W - L_outer_taper_point
    outer_straight_ref = c << gf.components.straight(length=outer_straight_len, cross_section=xs)
    # Connect its left end ("o1") to the bend's outer port ("o2").
    outer_straight_ref.connect("o1", bend_ref.ports["o2"])

    # Add the pointed taper to the right end of the outer straight.
    # Taper from full width (1 * spine_width) down to zero width.
    outer_taper_ref = c << gf.components.taper(length=L_outer_taper_point, width1=1, width2=0, cross_section=xs)
    # Connect taper's wide end ("o1") to the outer straight's right end ("o2").
    outer_taper_ref.connect("o1", outer_straight_ref.ports["o2"])

    # 3. Inner Straight Waveguide (from bend to blunt end on right, with comb)
    # This segment runs from the bend's inner port (o1) to the right edge of the device (W/2).
    # Its total length is W.
    inner_straight_ref = c << gf.components.straight(length=W, cross_section=xs)
    # Connect its left end ("o1") to the bend's inner port ("o1").
    inner_straight_ref.connect("o1", bend_ref.ports["o1"])

    # 4. Comb Teeth on the Inner Straight Segment
    # The comb teeth are on the inner straight, extending downwards (for the top arm).
    # They are positioned towards the right end of the inner straight.
    
    # Calculate total horizontal length occupied by all teeth and their gaps.
    comb_active_length = num_teeth * tooth_width + (num_teeth - 1) * tooth_gap

    # Calculate the x-coordinate for the leftmost edge of the first tooth.
    # This ensures the rightmost edge of the last tooth is at (W/2 - comb_x_offset_from_right).
    comb_section_start_x = (W / 2) - comb_x_offset_from_right - comb_active_length
    
    # Y-coordinate for the attachment point of the teeth (bottom edge of the inner straight).
    y_comb_attachment = y_inner_path - xs.width / 2 

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
    gap_vertical = 0.05      # Vertical gap between elements (central bar, inner spine, outer spine)
    spine_width = 0.1        # Width of the main waveguide spines (inner and outer)
    radius_bend = 0.075      # Radius of the 180-degree circular bend

    # Parameters for features
    L_outer_taper_point = 0.5        # Length of the pointed taper on the outer waveguide's right end
    comb_x_offset_from_right = 0.5   # Horizontal offset of the comb teeth from the right edge

    # Comb teeth parameters
    num_teeth = 26                   # Number of teeth in the comb
    tooth_width = 0.05               # Width of each individual tooth
    tooth_gap = 0.05                 # Horizontal spacing between teeth
    tooth_height = 0.15              # Vertical extent of each tooth

    # 1. Central Bar
    c << gf.components.rectangle(size=(W, center_bar_height), layer=(1, 0), centered=True)

    # 2. Top Arm
    # Instantiate the 'top_arm_design' with the derived parameters.
    c << top_arm_design(
        W, center_bar_height, gap_vertical, spine_width, radius_bend, 
        L_outer_taper_point, comb_x_offset_from_right,
        num_teeth, tooth_width, tooth_gap, tooth_height,
        layer=(1, 0)
    )

    # 3. Bottom Arm
    # Create another instance of top_arm_design and mirror it across the x-axis.
    # This automatically flips its vertical position and makes the teeth point upwards.
    bottom_arm_ref = c << top_arm_design(
        W, center_bar_height, gap_vertical, spine_width, radius_bend, 
        L_outer_taper_point, comb_x_offset_from_right,
        num_teeth, tooth_width, tooth_gap, tooth_height,
        layer=(1, 0)
    )
    bottom_arm_ref.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across the x-axis

    return c

# Create the device and save the GDS file
if __name__ == "__main__":
    device = custom_device()
    device.write_gds("custom_device.gds")
    # To visualize the device, uncomment the line below and run in an environment
    # with a GDS viewer configured (e.g., KLayout, LVS).
    # device.show()