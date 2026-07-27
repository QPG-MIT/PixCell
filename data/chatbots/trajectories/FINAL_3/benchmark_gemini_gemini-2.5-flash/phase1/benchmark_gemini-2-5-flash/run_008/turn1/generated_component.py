import gdsfactory as gf

@gf.cell
def parallel_waveguide_s_bends(
    waveguide_width: float = 0.5,
    gap: float = 0.5,
    s_bend_horizontal_length: float = 30.0,
    straight_horizontal_length: float = 60.0,
    total_vertical_span: float = 4.0,
    # Renamed parameter to avoid potential shadowing with the resolved cross-section object
    cross_section_spec: gf.cross_section.CrossSectionSpec = "strip"
) -> gf.Component:
    """
    Creates a component with two parallel waveguides connected by S-bends at both ends.

    The device starts with two widely separated waveguides, which then curve
    towards each other via S-bends to form two parallel straight segments,
    and finally curve outwards again via S-bends.

    Args:
        waveguide_width: The width of the individual waveguides.
        gap: The gap between the two parallel straight waveguides.
        s_bend_horizontal_length: The horizontal length (dx) of each S-bend.
        straight_horizontal_length: The horizontal length of the central parallel straight segments.
        total_vertical_span: The total vertical extent of the component,
                             from the top edge of the top input/output waveguide
                             to the bottom edge of the bottom input/output waveguide.
        cross_section_spec: The cross-section definition for the waveguides. Can be a string or a CrossSection object.

    Returns:
        A GDSFactory Component with the defined geometry.
    """
    c = gf.Component("parallel_waveguide_s_bends")

    # --- FIX START ---
    # Resolve cross-section: Be more explicit for the "strip" case.
    if isinstance(cross_section_spec, str):
        if cross_section_spec == "strip":
            # Explicitly create a strip cross-section with the desired width
            xs = gf.cross_section.strip(width=waveguide_width)
        else:
            # For other string specifications, use the general resolver
            xs = gf.get_cross_section(cross_section_spec, width=waveguide_width)
    else:
        # If a CrossSection object is already provided, use it directly.
        # Note: If the provided object's width should be overridden, additional logic would be needed here.
        xs = cross_section_spec
    # --- FIX END ---

    # Calculate the vertical offset (dy) for the S-bends.
    # We define the y-coordinates for the centerlines of the waveguides:

    # 1. Input/Output waveguide centerlines (at the device's edges):
    # The total_vertical_span (4um) includes the full width of the top and bottom waveguides.
    # The y-origin is at the center of the total vertical span.
    y_input_output_top_centerline = (total_vertical_span / 2) - (waveguide_width / 2)
    y_input_output_bottom_centerline = -((total_vertical_span / 2) - (waveguide_width / 2))

    # 2. Central parallel waveguide centerlines:
    # The two parallel waveguides have a gap between them.
    # These are centered around y=0.
    y_central_top_centerline = (waveguide_width / 2) + (gap / 2)
    y_central_bottom_centerline = -((waveguide_width / 2) + (gap / 2))

    # The S-bend's vertical displacement (dy) is the difference in centerline y-coordinates
    # between its start and end ports.
    # For the top waveguide, the left S-bend connects y_input_output_top_centerline to y_central_top_centerline.
    # The absolute value of this vertical offset:
    # (This is derived for verification, actual dy values are calculated below per bend)
    s_bend_vertical_offset_abs = abs(y_central_top_centerline - y_input_output_top_centerline)

    # --- Top Waveguide Path ---
    # 1. Left S-bend: Starts high (y_input_output_top_centerline), moves down to y_central_top_centerline.
    #    dy_top_left = y_central_top_centerline - y_input_output_top_centerline (will be negative).
    s_bend_left_top = c << gf.components.bend_s(
        size=(s_bend_horizontal_length, y_central_top_centerline - y_input_output_top_centerline),
        cross_section=xs
    )
    # Position the 'o1' port of this S-bend to the correct starting y-coordinate.
    s_bend_left_top.movey(y_input_output_top_centerline)

    # 2. Central Straight Segment: Connects from the left S-bend.
    straight_top = c << gf.components.straight(
        length=straight_horizontal_length,
        cross_section=xs
    )
    straight_top.connect("o1", s_bend_left_top.ports["o2"])

    # 3. Right S-bend: Starts at y_central_top_centerline, moves up to y_input_output_top_centerline.
    #    dy_top_right = y_input_output_top_centerline - y_central_top_centerline (will be positive).
    s_bend_right_top = c << gf.components.bend_s(
        size=(s_bend_horizontal_length, y_input_output_top_centerline - y_central_top_centerline),
        cross_section=xs
    )
    s_bend_right_top.connect("o1", straight_top.ports["o2"])

    # --- Bottom Waveguide Path ---
    # 1. Left S-bend: Starts low (y_input_output_bottom_centerline), moves up to y_central_bottom_centerline.
    #    dy_bottom_left = y_central_bottom_centerline - y_input_output_bottom_centerline (will be positive).
    s_bend_left_bottom = c << gf.components.bend_s(
        size=(s_bend_horizontal_length, y_central_bottom_centerline - y_input_output_bottom_centerline),
        cross_section=xs
    )
    # Position the 'o1' port of this S-bend to the correct starting y-coordinate.
    s_bend_left_bottom.movey(y_input_output_bottom_centerline)

    # 2. Central Straight Segment: Connects from the left S-bend.
    straight_bottom = c << gf.components.straight(
        length=straight_horizontal_length,
        cross_section=xs
    )
    straight_bottom.connect("o1", s_bend_left_bottom.ports["o2"])

    # 3. Right S-bend: Starts at y_central_bottom_centerline, moves down to y_input_output_bottom_centerline.
    #    dy_bottom_right = y_input_output_bottom_centerline - y_central_bottom_centerline (will be negative).
    s_bend_right_bottom = c << gf.components.bend_s(
        size=(s_bend_horizontal_length, y_input_output_bottom_centerline - y_central_bottom_centerline),
        cross_section=xs
    )
    s_bend_right_bottom.connect("o1", straight_bottom.ports["o2"])

    # Expose ports for external connection
    c.add_port("o1_top", port=s_bend_left_top.ports["o1"])
    c.add_port("o2_top", port=s_bend_right_top.ports["o2"])
    c.add_port("o1_bottom", port=s_bend_left_bottom.ports["o1"])
    c.add_port("o2_bottom", port=s_bend_right_bottom.ports["o2"])

    return c

# Define the footprint constraints
footprint_um = [120, 4]

# Instantiate the component with parameters derived from the image and footprint
component = parallel_waveguide_s_bends(
    waveguide_width=0.5,
    gap=0.5,
    s_bend_horizontal_length=30.0,
    straight_horizontal_length=60.0,
    total_vertical_span=footprint_um[1], # Use the height from the footprint constraint
    cross_section_spec="strip" # Use the renamed parameter
)

# You can uncomment the following lines to visualize the component or save it to a GDS file
# gf.show(component)
# component.write_gds("parallel_waveguide_s_bends.gds")

# Verification of component's bounding box against the footprint
bbox = component.bbox
# Check width
calculated_width = bbox[1][0] - bbox[0][0]
# Check height
calculated_height = bbox[1][1] - bbox[0][1]

print(f"Component bounding box: {bbox}")
print(f"Calculated width: {calculated_width} um, Expected width: {footprint_um[0]} um")
print(f"Calculated height: {calculated_height} um, Expected height: {footprint_um[1]} um")

assert abs(calculated_width - footprint_um[0]) < 1e-9, f"Width mismatch: {calculated_width} vs {footprint_um[0]}"
assert abs(calculated_height - footprint_um[1]) < 1e-9, f"Height mismatch: {calculated_height} vs {footprint_um[1]}"