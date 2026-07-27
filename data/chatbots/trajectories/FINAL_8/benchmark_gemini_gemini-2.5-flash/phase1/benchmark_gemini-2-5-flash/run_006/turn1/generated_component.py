import gdsfactory as gf
from gdsfactory.typings import LayerSpec

@gf.cell
def multi_line_structure(
    thin_width: float = 0.1,  # Width of the thinner lines
    thick_width: float = 0.2, # Width of the thickest lines
    gap: float = 0.05,        # Gap between lines within a structure
    wide_gap: float = 0.1,    # Wider gap between central lines block and top/bottom structures
    central_line_length: float = 60.0, # Length of the straight central sections (X-dimension)
    bend_section_dx: float = 30.0, # Horizontal length of each curved section (X-dimension)
    dy_bend_vertical_extension: float = 0.975, # Vertical extension of the path center at the curve tips
    smooth_radius: float = 10.0, # Smoothing radius for path.smooth, controls curve tightness
    layer: LayerSpec = (1, 0),
) -> gf.Component:
    """
    Recreates the multi-line geometry from the provided image using GDSFactory.

    The geometry consists of:
    1. Four central parallel horizontal lines.
    2. A top structure with one thick line and three thinner lines,
       which has a central straight section and two ends curving upwards.
    3. A bottom structure symmetric to the top one, curving downwards.

    The design is parametrically constructed to fit within a total footprint
    of [120.0, 4.0] um.

    Args:
        thin_width: Width of the thinner lines.
        thick_width: Width of the thickest lines.
        gap: Gap between lines within a multi-line structure.
        wide_gap: Wider gap separating the central lines from the top/bottom structures.
        central_line_length: Horizontal length of the straight middle section.
        bend_section_dx: Horizontal length of each curved section at the ends.
                         Total width = 2 * bend_section_dx + central_line_length.
        dy_bend_vertical_extension: Vertical distance the path center extends at the curve tips
                                    to meet the total height constraint.
        smooth_radius: Radius parameter for `gf.path.smooth`, controls curve smoothness.
        layer: GDS layer for the geometry.

    Returns:
        A gf.Component containing the recreated geometry.
    """
    c = gf.Component("multi_line_structure")

    # --- 1. Validate horizontal dimensions ---
    total_expected_width = 2 * bend_section_dx + central_line_length
    if abs(total_expected_width - 120.0) > 1e-9:
        raise ValueError(f"Total width ({total_expected_width}) must be 120.0")

    # --- 2. Calculate vertical layout and y-coordinates ---
    # The entire component will be centered around y=0, with total height 4.0um (y_min=-2.0, y_max=2.0).

    # Height of one multi-line structure (top or bottom) in its straight section
    # Order: thick_line + 3*thin_lines + 3*gaps = 0.2 + 3*0.1 + 3*0.05 = 0.65 um
    height_multi_line_structure = thick_width + 3 * thin_width + 3 * gap

    # Height of the central 4 lines block (4*thin_lines + 3*gaps = 4*0.1 + 3*0.05 = 0.55 um)
    height_central_lines_block = 4 * thin_width + 3 * gap

    # Total height of the straight sections when stacked vertically
    total_straight_stack_height = (
        height_multi_line_structure  # Bottom structure
        + wide_gap
        + height_central_lines_block # Central lines
        + wide_gap
        + height_multi_line_structure  # Top structure
    ) # 0.65 + 0.1 + 0.55 + 0.1 + 0.65 = 2.05 um

    # Calculate starting y-position for the bottom-most edge of the entire straight stack
    # Centered around y=0, so bottom edge is at -total_straight_stack_height / 2.0
    current_y_bottom_edge = -total_straight_stack_height / 2.0 # -1.025

    # --- Calculate y-coordinates for the center of paths/lines ---

    # For the Bottom Structure's path (thick line on bottom)
    # The path itself follows the geometric center of its 0.65um height block.
    y_center_bottom_path_straight = current_y_bottom_edge + height_multi_line_structure / 2.0 # -1.025 + 0.325 = -0.7

    # Update current_y_bottom_edge to point to the bottom of the central lines block
    current_y_bottom_edge += height_multi_line_structure + wide_gap

    # For the Central Lines (4 thin lines)
    # Each central line will be a separate straight component, so we store their individual y-centers.
    y_coords_central_lines_centers = []
    for i in range(4):
        line_center_y = current_y_bottom_edge + thin_width / 2.0 + i * (thin_width + gap)
        y_coords_central_lines_centers.append(line_center_y) # e.g., -0.225, -0.075, 0.075, 0.225

    # Update current_y_bottom_edge to point to the bottom of the top structure block
    current_y_bottom_edge += height_central_lines_block + wide_gap

    # For the Top Structure's path (thick line on top)
    y_center_top_path_straight = current_y_bottom_edge + height_multi_line_structure / 2.0 # 0.275 + 0.325 = 0.7

    # --- 3. Create CrossSections for multi-line structures ---

    # CrossSection for the Top Structure (thick line on top, 3 thin lines below)
    # Offsets are relative to the path's center. Lowest edge of the stack (0.65um) is at -0.325.
    top_sections = [
        gf.cross_section.Section(width=thin_width, offset=-0.325 + thin_width/2, layer=layer), # Bottom-most thin line
        gf.cross_section.Section(width=thin_width, offset=-0.325 + thin_width + gap + thin_width/2, layer=layer),
        gf.cross_section.Section(width=thin_width, offset=-0.325 + 2*(thin_width + gap) + thin_width/2, layer=layer),
        gf.cross_section.Section(width=thick_width, offset=-0.325 + 3*(thin_width + gap) + thin_width + thick_width/2, layer=layer), # Top-most thick line
    ]
    top_xs = gf.cross_section.CrossSection(sections=top_sections)

    # CrossSection for the Bottom Structure (thick line on bottom, 3 thin lines above)
    bottom_sections = [
        gf.cross_section.Section(width=thick_width, offset=-0.325 + thick_width/2, layer=layer), # Bottom-most thick line
        gf.cross_section.Section(width=thin_width, offset=-0.325 + thick_width + gap + thin_width/2, layer=layer),
        gf.cross_section.Section(width=thin_width, offset=-0.325 + thick_width + 2*(thin_width + gap) + thin_width/2, layer=layer),
        gf.cross_section.Section(width=thin_width, offset=-0.325 + thick_width + 3*(thin_width + gap) + thin_width/2, layer=layer), # Top-most thin line
    ]
    bottom_xs = gf.cross_section.CrossSection(sections=bottom_sections)

    # --- 4. Create and place central horizontal lines ---
    xs_thin = gf.cross_section.cross_section(width=thin_width, layer=layer)
    x_start_central = bend_section_dx # X-coordinate where the straight central section begins

    for y_center in y_coords_central_lines_centers:
        line_ref = c << gf.components.straight(length=central_line_length, cross_section=xs_thin)
        line_ref.center = (x_start_central + central_line_length / 2.0, y_center) # Horizontally center the line

    # --- 5. Create and place top and bottom structures using Path extrusion ---
    # Path points define the center line for the CrossSection extrusion.
    # Structure: (x=0, y_extended) -> (x=bend_dx, y_straight) -> (x=bend_dx+central_len, y_straight) -> (x=120, y_extended)

    # Top structure path points
    top_path_points = [
        (0, y_center_top_path_straight + dy_bend_vertical_extension), # Far left, highest point
        (bend_section_dx, y_center_top_path_straight),                 # Start of straight section (x=30)
        (bend_section_dx + central_line_length, y_center_top_path_straight), # End of straight section (x=90)
        (120, y_center_top_path_straight + dy_bend_vertical_extension),# Far right, highest point
    ]
    # Create the smoothed path using gf.path.smooth and then extrude it
    smoothed_top_path = gf.path.smooth(top_path_points, radius=smooth_radius)
    path_top_component = gf.path.extrude(smoothed_top_path, cross_section=top_xs)
    c << path_top_component

    # Bottom structure path points (mirror of top vertically)
    bottom_path_points = [
        (0, y_center_bottom_path_straight - dy_bend_vertical_extension), # Far left, lowest point
        (bend_section_dx, y_center_bottom_path_straight),                 # Start of straight section (x=30)
        (bend_section_dx + central_line_length, y_center_bottom_path_straight), # End of straight section (x=90)
        (120, y_center_bottom_path_straight - dy_bend_vertical_extension),# Far right, lowest point
    ]
    # Create the smoothed path using gf.path.smooth and then extrude it
    smoothed_bottom_path = gf.path.smooth(bottom_path_points, radius=smooth_radius)
    path_bottom_component = gf.path.extrude(smoothed_bottom_path, cross_section=bottom_xs)
    c << path_bottom_component

    return c

# Example usage and footprint verification:
if __name__ == "__main__":
    component = multi_line_structure()
    component.write_gds("multi_line_structure.gds")

    # Verify footprint against the constraint [120.0, 4.0] um
    bbox = component.bbox
    actual_width = bbox[1][0] - bbox[0][0]
    actual_height = bbox[1][1] - bbox[0][1]

    print(f"Component bounding box (min_x, min_y), (max_x, max_y): {bbox}")
    print(f"Actual width: {actual_width:.3f} um")
    print(f"Actual height: {actual_height:.3f} um")

    # Assert that the dimensions match the footprint constraint within a small tolerance
    assert abs(actual_width - 120.0) < 1e-9, f"Width mismatch: Expected 120.0, Got {actual_width}"
    assert abs(actual_height - 4.0) < 1e-9, f"Height mismatch: Expected 4.0, Got {actual_height}"
    print("\nFootprint constraints met successfully.")

    # To visualize the component (requires KLayout or similar GDS viewer setup)
    # gf.show(component)