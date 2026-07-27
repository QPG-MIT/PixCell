import gdsfactory as gf

@gf.cell
def top_arm_design(
    W: float,
    center_bar_height: float,
    gap_vertical: float,
    outer_arm_width: float,
    inner_arm_width: float,
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

    # Define cross-sections
    # FIX: Set radius_min for xs_outer to allow for bends with radius_bend
    xs_outer = gf.cross_section.cross_section(width=outer_arm_width, layer=layer, radius_min=radius_bend)
    xs_inner = gf.cross_section.cross_section(width=inner_arm_width, layer=layer)

    # Calculate y-coordinates for the centerlines of the paths
    y_inner_straight_bottom_edge = center_bar_height / 2 + gap_vertical
    y_inner_path_centerline = y_inner_straight_bottom_edge + inner_arm_width / 2

    # The outer path's centerline is 2*radius_bend above the inner path's corresponding vertical level.
    y_outer_path_centerline = y_inner_path_centerline + 2 * radius_bend


    # 1. Outer Taper (Rightmost element)
    outer_taper_ref = c << gf.components.taper(length=L_outer_taper_point, width1=outer_arm_width, width2=0, layer=layer)
    outer_taper_ref.move(origin=outer_taper_ref.ports["o2"].center, destination=(W / 2, y_outer_path_centerline))

    # 2. Outer Straight Waveguide (from bend to taper)
    # The length of this straight segment is from where the bend ends horizontally to where the taper starts.
    # The bend's total horizontal extent on its 'outer' side is radius_bend.
    outer_straight_length = (W / 2 - L_outer_taper_point) - (-W / 2 + radius_bend)
    outer_straight_ref = c << gf.components.straight(length=outer_straight_length, cross_section=xs_outer)
    outer_straight_ref.connect("o2", outer_taper_ref.ports["o1"]) # Connect its right end to taper's wide end

    # 3. Left U-Bend (composed of two 90-degree bends)
    # 3a. Upper 90-degree bend: Connects `outer_straight_ref.o1` (left end) to the vertical segment of the U.
    # This bend needs to turn FROM left (180) TO down (270).
    # Default `bend_euler(angle=90)`: `o1` (0,R) ang 180; `o2` (R,0) ang 270.
    # This orientation is already correct for connecting a left-facing port to a down-facing port.
    bend_upper_left_ref = c << gf.components.bend_euler(radius=radius_bend, angle=90, cross_section=xs_outer)
    bend_upper_left_ref.connect("o1", outer_straight_ref.ports["o1"]) # Connect to left end of outer straight

    # 3b. Lower 90-degree bend: Connects the vertical segment of the U to the position of the inner straight.
    # This bend needs to turn FROM up (90) TO left (180).
    # Default `bend_euler(angle=90)`: `o1` (0,R) ang 180; `o2` (R,0) ang 270.
    # To get `o1` facing 90 and `o2` facing 180: Rotate by -90 degrees (clockwise).
    # After -90 deg rotation: `o1` is at (R,0) facing 90 deg; `o2` is at (0,R) facing 180 deg.
    bend_lower_left_comp = gf.components.bend_euler(radius=radius_bend, angle=90, cross_section=xs_outer).copy()
    bend_lower_left_comp.rotate(-90)
    bend_lower_left_ref = c << bend_lower_left_comp
    
    # Connect this bend's 'o1' (now facing 90 degrees) to the 'o2' of the previous bend (which faces 270 degrees).
    # The `connect` function will align them.
    bend_lower_left_ref.connect("o1", bend_upper_left_ref.ports["o2"])
    # `bend_lower_left_ref.o2` is now positioned at `(-W/2, y_inner_path_centerline)` and faces 180 degrees (left).
    # This port serves as a positional reference for the start of the inner straight, but it is not connected.


    # 4. Inner Straight Waveguide (This is the one with comb teeth)
    # This straight segment is independent and positioned.
    # It starts at x = -W/2 and extends to the right end where comb teeth are.
    inner_straight_total_length = (W/2 - comb_x_offset_from_right) - (-W/2)
    inner_straight_ref = c << gf.components.straight(length=inner_straight_total_length, cross_section=xs_inner)
    
    # FIX: Use move instead of connect, as this is a parallel, unconnected waveguide.
    # Position the inner straight's left end (o1) at the global coordinates (-W/2, y_inner_path_centerline).
    # The 'o1' port of a default straight component is at (0,0) and faces 180 degrees (left).
    # Moving its 'o1' to target ensures its leftmost point is at -W/2, and its centerline is at y_inner_path_centerline.
    inner_straight_ref.move(origin=inner_straight_ref.ports["o1"].center, destination=(-W/2, y_inner_path_centerline))

    # 5. Add the comb teeth.
    # Comb teeth are on the inner straight, extending downwards (for the top arm).
    
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
    center_bar_height = 0.1
    gap_vertical = 0.04      # Adjusted to fit H=0.7
    outer_arm_width = 0.15
    inner_arm_width = 0.05
    radius_bend = 0.08      # Adjusted to be > outer_arm_width/2

    # Parameters for features
    L_outer_taper_point = 0.5
    comb_x_offset_from_right = 0.5
    
    # Comb teeth parameters (Adjusted for better visual match)
    num_teeth = 20                   
    tooth_width = 0.06               
    tooth_gap = 0.03                 
    tooth_height = 0.15

    # 1. Central Bar
    c << gf.components.rectangle(size=(W, center_bar_height), layer=(1, 0), centered=True)

    # 2. Top Arm
    c << top_arm_design(
        W, center_bar_height, gap_vertical, 
        outer_arm_width, inner_arm_width, radius_bend, 
        L_outer_taper_point, comb_x_offset_from_right,
        num_teeth, tooth_width, tooth_gap, tooth_height,
        layer=(1, 0)
    )

    # 3. Bottom Arm
    bottom_arm_ref = c << top_arm_design(
        W, center_bar_height, gap_vertical, 
        outer_arm_width, inner_arm_width, radius_bend, 
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