import gdsfactory as gf

@gf.cell
def create_symmetric_structure():
    """
    Creates a symmetric structure with varying horizontal lengths in the outer sections
    and Euler bends for smoother curves, aiming to closely match the target image.
    This version fixes a component placement syntax error.
    """
    c = gf.Component("SymmetricStructure_V4_Fixed")

    # --- Parameters tuned to match footprint [120, 4] and visual aspect ratio ---
    
    # Central section
    n_center_lines = 5
    center_line_width = 0.1
    center_line_pitch = 0.2
    center_length = 100.0

    # Outer sections
    n_outer_lines_thin = 4
    base_line_width = 0.4
    outer_line_width = 0.1
    outer_line_pitch = 0.2
    
    bend_radius = 8.0
    bend_angle = 90
    
    # Base straight length to achieve a total width of ~120 um
    outer_straight_length_max = 104.0
    length_decrement = 4.0

    # Vertical placement
    group_gap = 0.2

    # --- 1. Create Central Lines component ---
    center_lines = gf.Component("CenterLines")
    for i in range(n_center_lines):
        rect = gf.components.rectangle(
            size=(center_length, center_line_width), layer=(1, 0)
        )
        rect_ref = center_lines.add_ref(rect)
        rect_ref.movey(i * center_line_pitch)
        
    center_lines.movey(-center_lines.center[1])

    # --- 2. Create Top Section component ---
    top_section = gf.Component("TopSection")

    def create_curved_line(cross_section, straight_len: float):
        """
        Helper function to create a bend-straight-bend symmetric shape.
        Uses Euler bends for smoother transitions and accepts a variable straight length.
        """
        line = gf.Component()
        bend = gf.components.bend_euler(
            radius=bend_radius, angle=bend_angle, p=0.5, cross_section=cross_section
        )
        straight = gf.components.straight(
            length=straight_len, cross_section=cross_section
        )
        
        b1 = line << bend
        s = line << straight
        b2 = line << bend
        
        s.connect("o1", b1.ports["o2"])
        b2.connect("o1", s.ports["o2"])
        b2.mirror()
        
        line.movex(-line.center[0])
        return line

    # Create cross-sections for the outer lines
    xs_base = gf.cross_section.cross_section(width=base_line_width, radius_min=bend_radius)
    xs_line = gf.cross_section.cross_section(width=outer_line_width, radius_min=bend_radius)
    
    # Create and place the thick base line (the longest one)
    base_line = create_curved_line(cross_section=xs_base, straight_len=outer_straight_length_max)
    base_ref = top_section << base_line
    base_ref.movey(-base_line.ymin)
    
    current_y_top = base_ref.ymax
    current_straight_len = outer_straight_length_max
    gap = outer_line_pitch - outer_line_width
    
    # Create and place the thinner, shorter lines above the base
    for _ in range(n_outer_lines_thin):
        current_straight_len -= length_decrement
        thin_line = create_curved_line(cross_section=xs_line, straight_len=current_straight_len)
        
        line_ref = top_section << thin_line
        line_ref.movey(current_y_top + gap - thin_line.ymin)
        current_y_top = line_ref.ymax

    # --- 3. Assemble the final component ---
    # FIX: Replaced the problematic '.d' syntax with standard '.move()' methods.
    
    # Place the central lines and move its center to the origin (0, 0)
    center_ref = c << center_lines
    center_ref.move(-center_ref.center)
    
    # Place the top section, aligning its horizontal center and positioning it above the central lines
    top_ref = c << top_section
    top_ref.movex(center_ref.center[0] - top_ref.center[0])
    top_ref.movey(center_ref.ymax + group_gap - top_ref.ymin)

    # Place and mirror the bottom section
    bottom_ref = c << top_section
    bottom_ref.mirror(p1=(0, 0), p2=(1, 0))
    
    # Align the bottom section's horizontal center and position it below the central lines
    bottom_ref.movex(center_ref.center[0] - bottom_ref.center[0])
    bottom_ref.movey(center_ref.ymin - group_gap - bottom_ref.ymax)
    
    return c

# --- Main execution block ---
if __name__ == "__main__":
    my_device = create_symmetric_structure()
    my_device.show()