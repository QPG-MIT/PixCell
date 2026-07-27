import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec
from gdsfactory.cross_section import Section

# Define device parameters
W = 120.0  # Total width
H = 4.0    # Total height

# Calculated line/gap widths and bend radius based on total height and bend factor
# The derivation in the previous thought process was:
# (2 * R_bend_factor + 29) * w = H
# Assuming R_bend_factor = 10 (i.e., R_bend = 10 * line_width)
# (2 * 10 + 29) * w = 4.0 => 49 * w = 4.0 => w = 4.0 / 49
line_width_global = 4.0 / 49 # Renamed global variable to avoid potential clash
gap_width_global = 4.0 / 49  # Renamed global variable
group_gap_width_global = 4.0 / 49
R_bend_global = 10 * line_width_global # Radius of Euler bends
L_vertical_arm_global = 0.0 # Length of straight vertical segment at ends of U-shape

# Derived parameters
pitch_global = line_width_global + gap_width_global
H_group_global = 5 * line_width_global + 4 * gap_width_global # Height of a 5-line group (9 * line_width)
dev_layer = (1, 0) # GDS layer for the device


@gf.cross_section.cross_section
def xs_five_lines_centered(
    lw: float = line_width_global, # Use 'lw' as local parameter name
    gw: float = gap_width_global,  # Use 'gw' as local parameter name
    layer=dev_layer
) -> CrossSectionSpec:
    """
    Cross-section with 5 parallel lines, centered around the path.
    Used for the middle group of straight lines.
    """
    sections = []
    pitch_local = lw + gw
    # Calculate offset for the lowest line so the whole group is centered
    total_height_of_group = 5 * lw + 4 * gw
    first_line_offset = -total_height_of_group / 2 + lw / 2

    for i in range(5): # 0 (bottom) to 4 (top)
        offset = first_line_offset + i * pitch_local
        sections.append(Section(width=lw, offset=offset, layer=layer)) # Pass 'lw' to Section
    return gf.cross_section.CrossSection(width=0, sections=sections, layer=None)


@gf.cross_section.cross_section
def xs_five_lines_outer_ref(
    lw: float = line_width_global,
    gw: float = gap_width_global,
    layer=dev_layer
) -> CrossSectionSpec:
    """
    Cross-section with 5 parallel lines, where offset=0 is the top-most line of the group.
    Subsequent sections are negatively offset (towards the bottom).
    Used for the top group with 'U'-shaped path.
    """
    sections = []
    pitch_local = lw + gw
    for i in range(5): # 0 (top-most) to 4 (bottom-most)
        offset = -i * pitch_local
        sections.append(Section(width=lw, offset=offset, layer=layer)) # Pass 'lw' to Section
    return gf.cross_section.CrossSection(width=0, sections=sections, layer=None)


@gf.cross_section.cross_section
def xs_five_lines_inner_ref(
    lw: float = line_width_global,
    gw: float = gap_width_global,
    layer=dev_layer
) -> CrossSectionSpec:
    """
    Cross-section with 5 parallel lines, where offset=0 is the bottom-most line of the group.
    Subsequent sections are positively offset (towards the top).
    Used for the bottom group with 'inverted U'-shaped path.
    """
    sections = []
    pitch_local = lw + gw
    for i in range(5): # 0 (bottom-most) to 4 (top-most)
        offset = i * pitch_local
        sections.append(Section(width=lw, offset=offset, layer=layer)) # Pass 'lw' to Section
    return gf.cross_section.CrossSection(width=0, sections=sections, layer=None)


@gf.cell
def custom_device():
    c = gf.Component("custom_device")

    # 1. Central group of 5 straight lines
    xs_mid = xs_five_lines_centered()
    # Create path from -W/2 to W/2 to ensure horizontal centering
    path_middle_centered = gf.Path([(x, 0) for x in gf.np.linspace(-W/2, W/2, 2)])
    c_middle_ref = c << gf.path.extrude(path_middle_centered, cross_section=xs_mid)


    # 2. Top group of 5 lines with curved ends
    xs_top = xs_five_lines_outer_ref()

    # Calculate y-coordinates for the path of the top-most line of P_top group.
    # The top-most line's centerline should be at Y = H/2 - line_width_global/2.
    y_outermost_horizontal_top = H/2 - line_width_global/2
    y_start_vertical_top_leg = y_outermost_horizontal_top - R_bend_global - L_vertical_arm_global

    # Define points for the 'U' shaped path of the top-most line.
    path_points_top = [
        (-W/2, y_start_vertical_top_leg),
        (-W/2, y_outermost_horizontal_top - R_bend_global),
        (-W/2 + R_bend_global, y_outermost_horizontal_top),
        (W/2 - R_bend_global, y_outermost_horizontal_top),
        (W/2, y_outermost_horizontal_top - R_bend_global),
        (W/2, y_start_vertical_top_leg)
    ]
    p_top_outer = gf.path.smooth(points=path_points_top, radius=R_bend_global, bend_factory=gf.path.euler)

    c_top_group_ref = c << gf.path.extrude(p_top_outer, cross_section=xs_top)

    # 3. Bottom group of 5 lines with curved ends (mirrored from top)
    xs_bottom = xs_five_lines_inner_ref()

    # Calculate y-coordinates for the path of the bottom-most line of P_bottom group.
    # The bottom-most line's centerline should be at Y = -H/2 + line_width_global/2.
    y_outermost_horizontal_bottom = -H/2 + line_width_global/2
    y_start_vertical_bottom_leg = y_outermost_horizontal_bottom + R_bend_global + L_vertical_arm_global

    # Define points for the 'inverted U' shaped path of the bottom-most line.
    path_points_bottom = [
        (-W/2, y_start_vertical_bottom_leg),
        (-W/2, y_outermost_horizontal_bottom + R_bend_global),
        (-W/2 + R_bend_global, y_outermost_horizontal_bottom),
        (W/2 - R_bend_global, y_outermost_horizontal_bottom),
        (W/2, y_outermost_horizontal_bottom + R_bend_global),
        (W/2, y_start_vertical_bottom_leg)
    ]
    p_bottom_outer = gf.path.smooth(points=path_points_bottom, radius=R_bend_global, bend_factory=gf.path.euler)

    c_bottom_group_ref = c << gf.path.extrude(p_bottom_outer, cross_section=xs_bottom)

    return c

# Create and visualize the device
if __name__ == "__main__":
    device = custom_device()
    device.plot() # Show in matplotlib window
    # device.write_gds("custom_device.gds") # Uncomment to save to a GDS file