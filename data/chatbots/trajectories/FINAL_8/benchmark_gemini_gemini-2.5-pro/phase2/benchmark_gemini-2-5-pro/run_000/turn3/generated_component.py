import gdsfactory as gf

@gf.cell
def create_symmetric_structure():
    """
    Creates a symmetric structure with a central group of straight lines
    and two outer groups of curved lines, resembling the target image.
    """
    c = gf.Component("SymmetricStructure")

    # --- Parameters tuned to visually match the target image ---
    # Central section
    n_center_lines = 5
    center_line_width = 0.5
    center_line_pitch = 1.0  # width + gap
    center_length = 90.0

    # Outer sections
    n_outer_lines = 5
    outer_line_width = 0.2
    outer_line_pitch = 0.6  # width + gap
    solid_base_width = 1.2
    bend_radius = 8.0
    bend_angle = 90
    straight_length = 60.0
    
    # Vertical placement
    group_gap = 1.0

    # --- 1. Create Central Lines component ---
    center_lines = gf.Component("CenterLines")
    for i in range(n_center_lines):
        y_pos = i * center_line_pitch
        rect = center_lines.add_ref(
            gf.components.rectangle(
                size=(center_length, center_line_width), layer=(1, 0)
            )
        )
        rect.movey(y_pos)
    # Center the whole group vertically around y=0
    center_lines.movey(-center_lines.center[1])

    # --- 2. Create Top Section component ---
    top_section = gf.Component("TopSection")

    def create_curved_line(cross_section):
        """Helper function to create a bend-straight-bend symmetric shape."""
        line = gf.Component()
        bend = gf.components.bend_circular(
            radius=bend_radius, angle=bend_angle, cross_section=cross_section
        )
        straight = gf.components.straight(
            length=straight_length, cross_section=cross_section
        )
        
        b1 = line << bend
        s = line << straight
        b2 = line << bend
        
        s.connect("o1", b1.ports["o2"])
        b2.connect("o1", s.ports["o2"])
        b2.mirror()
        
        # Center the created line component horizontally
        line.movex(-line.center[0])
        return line

    # Create and place the solid base line in the top section
    xs_solid = gf.cross_section.cross_section(width=solid_base_width, radius_min=bend_radius)
    solid_base_line = create_curved_line(cross_section=xs_solid)
    solid_ref = top_section << solid_base_line
    # Position the solid base so its bottom edge is at y=0 for easy stacking
    solid_ref.movey(-solid_base_line.ymin)

    # Create and place the thinner lines above the base
    xs_line = gf.cross_section.cross_section(width=outer_line_width, radius_min=bend_radius)
    thin_line = create_curved_line(cross_section=xs_line)
    
    gap = outer_line_pitch - outer_line_width
    current_y_top = solid_ref.ymax  # Top of the last placed element

    for _ in range(n_outer_lines):
        line_ref = top_section << thin_line
        # Move the new line so its bottom is at current_y_top + gap
        line_ref.movey(current_y_top + gap - thin_line.ymin)
        current_y_top = line_ref.ymax  # Update the top position

    # --- 3. Assemble final component ---
    # Place the central lines at the origin
    center_ref = c << center_lines
    
    # FIX: The `move` function expects a coordinate tuple (dx, dy).
    # The unary minus operator cannot be applied to a tuple directly.
    # Instead, we negate each element of the center tuple individually
    # to create the correct translation vector to move the center to (0,0).
    center_ref.move((-center_ref.center[0], -center_ref.center[1]))


    # Place the top section above the central lines
    top_ref = c << top_section
    top_ref.movey(center_ref.ymax + group_gap - top_ref.ymin)
    top_ref.movex(-top_ref.center[0])  # Align centers horizontally

    # Mirror top section for the bottom part
    bottom_ref = c << top_section
    bottom_ref.mirror(p1=(0, 0), p2=(1, 0))  # Reflect across x-axis
    
    # Position bottom section below the central lines
    bottom_ref.movey(center_ref.ymin - group_gap - bottom_ref.ymax)
    bottom_ref.movex(-bottom_ref.center[0])  # Align centers horizontally

    return c

# --- Main execution block ---
if __name__ == "__main__":
    # Instantiate the component by calling the function
    my_device = create_symmetric_structure()
    
    # Write the component to a GDS file
    my_device.write_gds("device_recreation.gds")

    # Optional: show the component in the KLayout viewer if installed
    my_device.show()