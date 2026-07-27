import gdsfactory as gf

@gf.cell
def top_arm_design(
    W: float,
    center_bar_height: float,
    gap_vertical: float,
    spine_width: float,
    radius_bend: float,
    L_taper: float,
    num_teeth: int,
    tooth_width: float,
    tooth_gap: float,
    tooth_height: float,
    layer: tuple = (1, 0),
) -> gf.Component:
    """
    Creates one of the U-shaped arms with comb teeth and a taper.
    This design is for the top arm, positioned relative to a global (0,0) center.
    Mirroring this component will create the bottom arm correctly.
    """
    c = gf.Component("top_arm")
    
    # FIX: Add radius_min to the cross_section definition to allow small bends
    xs = gf.cross_section.cross_section(width=spine_width, layer=layer, radius_min=radius_bend)

    # Calculate y-coordinates for the centerlines of the paths
    y_inner_path = center_bar_height / 2 + gap_vertical + spine_width / 2
    # The vertical separation of centerlines in the bend is 2 * radius_bend
    y_outer_path = y_inner_path + 2 * radius_bend 

    # 1. Main 180-degree Bend (left side of the arm)
    # bend_circular(angle=180) has 'o1' at (0,0) facing 0 deg, 'o2' at (0, 2*radius) facing 0 deg.
    bend_ref = c << gf.components.bend_circular(radius=radius_bend, angle=180, cross_section=xs)
    
    # Move the bend so its 'o1' (inner, lower port) is at the leftmost edge, at y_inner_path
    bend_ref.move(origin=bend_ref.ports["o1"].center, destination=(-W / 2, y_inner_path))
    # Now bend_ref.ports["o1"] is at (-W/2, y_inner_path), facing 0 deg.
    # And bend_ref.ports["o2"] is at (-W/2, y_outer_path), facing 0 deg.

    # 2. Taper Component (left side of inner straight)
    # Taper from width 0 to spine_width over length L_taper
    # gf.components.taper uses width1/width2 as multipliers of cross_section.width if cross_section is provided.
    # So width1=0 means 0 * spine_width, width2=1 means 1 * spine_width.
    taper_ref = c << gf.components.taper(length=L_taper, width1=0, width2=1, cross_section=xs)
    
    # Connect taper's narrow end ("o1") to the bend's inner port ("o1")
    taper_ref.connect("o1", bend_ref.ports["o1"])
    # After connection:
    # taper_ref.ports["o1"] is at (-W/2, y_inner_path), facing 0 deg.
    # taper_ref.ports["o2"] (wide end) is at (-W/2 + L_taper, y_inner_path), facing 0 deg.

    # 3. Inner Straight Segment (from taper end to right edge)
    # Its length is from the end of the taper to W/2.
    straight_inner_len = W - L_taper
    straight_inner_ref = c << gf.components.straight(length=straight_inner_len, cross_section=xs)
    
    # Connect inner straight's left end ("o1") to the taper's wide end ("o2")
    straight_inner_ref.connect("o1", taper_ref.ports["o2"])
    # After connection:
    # straight_inner_ref.ports["o1"] is at (-W/2 + L_taper, y_inner_path), facing 180 deg. (taper.o2 faces 0, so straight is flipped)
    # This is correct for connection, it aligns the ports.
    # straight_inner_ref.ports["o2"] is at (W/2, y_inner_path), facing 0 deg.

    # 4. Outer Straight Segment (from bend end to right edge)
    # Its length is the full width W.
    straight_outer_ref = c << gf.components.straight(length=W, cross_section=xs)
    
    # Connect outer straight's left end ("o1") to the bend's outer port ("o2")
    straight_outer_ref.connect("o1", bend_ref.ports["o2"])
    # After connection:
    # straight_outer_ref.ports["o1"] is at (-W/2, y_outer_path), facing 180 deg. (bend.o2 faces 0, so straight is flipped)
    # This is correct for connection.
    # straight_outer_ref.ports["o2"] is at (W/2, y_outer_path), facing 0 deg.

    # 5. Comb Teeth on the Outer Straight Segment
    # The comb is centered along the full length W of the outer straight.
    comb_active_length = num_teeth * tooth_width + (num_teeth - 1) * tooth_gap
    comb_start_offset = (W - comb_active_length) / 2
    
    # The comb teeth extend downwards from the bottom edge of the outer straight.
    # straight_outer_ref.ports["o1"].center[0] is -W/2, straight_outer_ref.ports["o1"].center[1] is y_outer_path.
    y_comb_attachment = straight_outer_ref.ports["o1"].center[1] - xs.width / 2

    for i in range(num_teeth):
        tooth_x_pos = (-W / 2) + comb_start_offset + i * (tooth_width + tooth_gap) + tooth_width / 2
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

    # Overall device footprint dimensions
    W = 18.24  # Total width
    H = 0.7    # Total height (for reference, not directly used for placement but derived from it)

    # Device component parameters
    center_bar_height = 0.1
    gap_vertical = 0.05
    spine_width = 0.15
    radius_bend = 0.05 

    L_taper = 1.0

    # Comb teeth parameters
    num_teeth = 26
    tooth_width = 0.05
    tooth_gap = 0.05
    tooth_height = 0.15

    # 1. Central Bar
    c << gf.components.rectangle(size=(W, center_bar_height), layer=(1, 0), centered=True)

    # 2. Top Arm
    c << top_arm_design(
        W, center_bar_height, gap_vertical, spine_width, radius_bend, L_taper,
        num_teeth, tooth_width, tooth_gap, tooth_height,
        layer=(1, 0)
    )

    # 3. Bottom Arm
    # Create another instance of top_arm_design and mirror it.
    bottom_arm_ref = c << top_arm_design(
        W, center_bar_height, gap_vertical, spine_width, radius_bend, L_taper,
        num_teeth, tooth_width, tooth_gap, tooth_height,
        layer=(1, 0)
    )
    # Mirroring across the x-axis (p1=(0,0), p2=(1,0)) will flip the y-coordinates.
    # This correctly positions the bottom arm and makes its teeth extend upwards.
    bottom_arm_ref.mirror(p1=(0, 0), p2=(1, 0))

    return c

# Create the device and save the GDS file
if __name__ == "__main__":
    device = custom_device()
    device.write_gds("custom_device.gds")
    # To visualize the device, uncomment the line below and run in an environment
    # with a GDS viewer configured (e.g., KLayout, LVS).
    # device.show()