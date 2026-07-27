import gdsfactory as gf

@gf.cell
def custom_device_from_image(
    line_width: float = 0.17,
    gap_width: float = 0.17,
    total_length: float = 120.0,
    total_height: float = 4.0,
    bend_radius: float = 10.0, # Radius for the curved sections at the ends
    straight_middle_length: float = 80.0 # Length of the purely straight middle section
) -> gf.Component:
    """
    Recreates the geometry from the provided image using GDSFactory parametric functions.

    The device consists of:
    - 4 central parallel straight lines.
    - Top and bottom 'frames' at the ends, each containing 4 parallel curved lines.

    The component is centered at (0,0).
    """
    c = gf.Component("device_from_image")

    # Calculate line offsets based on total_height, line_width, and gap_width
    num_lines_total = 12
    num_gaps_total = 11
    occupied_height = num_lines_total * line_width + num_gaps_total * gap_width
    
    # Calculate Y-offsets for the center of each line, from bottom to top
    line_offsets = []
    # Start current_y from the bottom edge of the stack, then add half a line_width to get the center
    current_y = -occupied_height / 2 + line_width / 2 

    for _ in range(num_lines_total):
        line_offsets.append(current_y)
        current_y += (line_width + gap_width)

    # 1. Create the central 4 straight lines
    # These are lines 4, 5, 6, 7 from the line_offsets list (0-indexed)
    # These lines span the full 120um horizontally.
    xs_central_lines = gf.cross_section.cross_section(sections=[
        gf.cross_section.Section(width=line_width, offset=line_offsets[4], layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[5], layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[6], layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[7], layer=(1, 0)),
    ])
    path_straight_central = gf.path.straight(length=total_length)
    
    # Create the component definition and add its reference to 'c'
    central_lines_def = gf.path.extrude(path_straight_central, xs_central_lines)
    central_lines_ref = c << central_lines_def
    central_lines_ref.movex(-total_length / 2) # Center the component horizontally

    # 2. Create the top and bottom 'frame' lines for the curved ends
    # These frames each contain 4 lines.
    # Lines 8, 9, 10, 11 for the top frame.
    # Lines 0, 1, 2, 3 for the bottom frame.

    # Midpoint Y for the top frame group (relative to y=0 of the overall component)
    y_mid_top_frame_group = (line_offsets[8] + line_offsets[11]) / 2
    # Midpoint Y for the bottom frame group (relative to y=0 of the overall component)
    y_mid_bottom_frame_group = (line_offsets[0] + line_offsets[3]) / 2

    # Cross-sections for the frame groups, centered around their respective path's y=0.
    # The offset here is relative to the *path's* Y, not absolute Y.
    xs_top_frame_group = gf.cross_section.cross_section(sections=[
        gf.cross_section.Section(width=line_width, offset=line_offsets[8] - y_mid_top_frame_group, layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[9] - y_mid_top_frame_group, layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[10] - y_mid_top_frame_group, layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[11] - y_mid_top_frame_group, layer=(1, 0)),
    ])
    xs_bottom_frame_group = gf.cross_section.cross_section(sections=[
        gf.cross_section.Section(width=line_width, offset=line_offsets[0] - y_mid_bottom_frame_group, layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[1] - y_mid_bottom_frame_group, layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[2] - y_mid_bottom_frame_group, layer=(1, 0)),
        gf.cross_section.Section(width=line_width, offset=line_offsets[3] - y_mid_bottom_frame_group, layer=(1, 0)),
    ])

    # Define the path for the top and bottom frame groups, which creates the 'waist' effect.
    # The path should start and end at the same Y-level (relative to its own (0,0)),
    # but dip/rise in the middle to create the curve.

    # Calculate the length of the horizontal straight segments at the outer ends
    # This calculation ensures the total horizontal span is `total_length`.
    L_outer_straight = (total_length - 2 * bend_radius - straight_middle_length) / 2
    
    # Add a check to ensure L_outer_straight is positive, otherwise the bend_radius/straight_middle_length are too large
    if L_outer_straight < 0:
        raise ValueError(
            f"L_outer_straight calculated to be {L_outer_straight:.2f}um. "
            "Ensure total_length > (2 * bend_radius + straight_middle_length) "
            f"(i.e., {total_length} > {2*bend_radius + straight_middle_length}um). "
            "Consider reducing bend_radius or straight_middle_length, or increasing total_length."
        )

    # Path for the top frame (centerline starts at y=0, dips down, goes straight, curves up, ends at y=0)
    p_top_frame = gf.Path()
    p_top_frame.append(gf.path.straight(length=L_outer_straight))
    p_top_frame.append(gf.path.euler(radius=bend_radius, angle=-90)) # Curve downwards
    p_top_frame.append(gf.path.straight(length=straight_middle_length))
    p_top_frame.append(gf.path.euler(radius=bend_radius, angle=90)) # Curve upwards
    p_top_frame.append(gf.path.straight(length=L_outer_straight))

    # Path for the bottom frame (centerline starts at y=0, rises up, goes straight, curves down, ends at y=0)
    p_bottom_frame = gf.Path()
    p_bottom_frame.append(gf.path.straight(length=L_outer_straight))
    p_bottom_frame.append(gf.path.euler(radius=bend_radius, angle=90)) # Curve upwards
    p_bottom_frame.append(gf.path.straight(length=straight_middle_length))
    p_bottom_frame.append(gf.path.euler(radius=bend_radius, angle=-90)) # Curve downwards
    p_bottom_frame.append(gf.path.straight(length=L_outer_straight))

    # Component for the top frame (4 lines):
    # Create the component definition
    top_frame_def = gf.path.extrude(p_top_frame, xs_top_frame_group)
    # Add a reference to 'c' and get the reference object
    top_frame_ref = c << top_frame_def
    # Position its centerline (which dips) to be centered horizontally and vertically at y_mid_top_frame_group when flat
    top_frame_ref.movey(y_mid_top_frame_group)
    top_frame_ref.movex(-total_length/2) # Center it horizontally (path starts at 0,0, spans total_length)

    # Component for the bottom frame (4 lines):
    # Create the component definition
    bottom_frame_def = gf.path.extrude(p_bottom_frame, xs_bottom_frame_group)
    # Add a reference to 'c' and get the reference object
    bottom_frame_ref = c << bottom_frame_def
    # Position its centerline (which rises) to be centered horizontally and vertically at y_mid_bottom_frame_group when flat
    bottom_frame_ref.movey(y_mid_bottom_frame_group)
    bottom_frame_ref.movex(-total_length/2) # Center it horizontally (path starts at 0,0, spans total_length)

    # All components (central, top frame, bottom frame) have already been added to `c`
    # using the `c << component_definition` syntax. No further `c.add_ref()` calls are needed.

    return c

if __name__ == "__main__":
    # Create the device
    device = custom_device_from_image()

    # View in KLayout (if installed)
    device.show()

    # Save to GDS file
    device.write_gds("custom_device_from_image.gds")

    # Print relevant parameters
    print(f"Device ports: {device.ports}")
    print(f"Device bounds: {device.bbox}")