import gdsfactory as gf
import numpy as np

@gf.cell
def create_waisted_line_structure():
    """
    Creates a waisted structure made of multiple parallel lines,
    resembling the provided image.

    The structure consists of a central straight section and two flared
    sections on either side, all composed of parallel waveguides.
    It is built by connecting bundles of S-bends to a central
    straight waveguide bundle.
    """
    c = gf.Component()

    # Define the geometric parameters based on the footprint and image analysis
    total_width = 120.0
    total_height = 4.0
    center_straight_length = 40.0
    num_lines_per_side = 5
    line_width = 0.15
    
    # Gaps between lines
    gap_inter_line = 0.15  # Gap between lines within the top or bottom group
    gap_center = 0.2       # Gap between the top and bottom groups at the center

    # Define the cross-section for a single line
    xs = gf.cross_section.cross_section(width=line_width)

    # --- Calculate Y-coordinates and displacements ---

    # Y-coordinates for the top group of lines in the central straight section
    pitch_center = line_width + gap_inter_line
    y_start_pos = gap_center / 2 + line_width / 2
    y_center_top = [y_start_pos + i * pitch_center for i in range(num_lines_per_side)]

    # Y-coordinates for the top group of lines at the outer edges.
    # The lines spread out to fill the available vertical space up to the footprint edge.
    # The center of the outermost line must be at total_height/2 - line_width/2.
    y_max_centerline = total_height / 2 - line_width / 2
    
    # FIX: Use np.linspace for a robust and clear distribution of end positions.
    # The innermost line of the top group (i=0) does not change its y-position, 
    # while the others spread out linearly up to the maximum calculated position.
    y_end_top = list(np.linspace(y_center_top[0], y_max_centerline, num_lines_per_side))

    # Calculate the vertical displacement (dy) for each S-bend
    dy_top = [y_end - y_center for y_end, y_center in zip(y_end_top, y_center_top)]

    # The horizontal length of the flared sections
    flare_dx = (total_width - center_straight_length) / 2

    # --- Build the Component ---

    # 1. Create a component for the central straight section to hold the ports
    center_straights = gf.Component("center_straights")
    for i in range(num_lines_per_side):
        straight_wg = gf.components.straight(length=center_straight_length, cross_section=xs)
        
        # Add top straight line and its ports
        s_ref_top = center_straights << straight_wg
        s_ref_top.movey(y_center_top[i])
        center_straights.add_port(f"t_o1_{i}", port=s_ref_top.ports["o1"])
        center_straights.add_port(f"t_o2_{i}", port=s_ref_top.ports["o2"])

        # Add bottom straight line and its ports (symmetrical)
        s_ref_bot = center_straights << straight_wg
        s_ref_bot.movey(-y_center_top[i])
        center_straights.add_port(f"b_o1_{i}", port=s_ref_bot.ports["o1"])
        center_straights.add_port(f"b_o2_{i}", port=s_ref_bot.ports["o2"])

    # Add the central section to the main component
    center_ref = c << center_straights

    # 2. Create and connect the flared sections using S-bends
    for i in range(num_lines_per_side):
        # Create a single S-bend prototype for the current line's displacement
        # If dy is zero, bend_s will return a straight, which is the desired behavior.
        s_bend = gf.components.bend_s(size=(flare_dx, dy_top[i]), cross_section=xs)

        # Right side flares (top and bottom)
        bend_ref_r_top = c << s_bend
        bend_ref_r_top.connect("o1", center_ref.ports[f"t_o2_{i}"])

        bend_ref_r_bot = c << s_bend
        bend_ref_r_bot.mirror(p1=(0, 0), p2=(1, 0)) # Mirror vertically
        bend_ref_r_bot.connect("o1", center_ref.ports[f"b_o2_{i}"])

        # Left side flares (top and bottom)
        bend_ref_l_top = c << s_bend
        bend_ref_l_top.mirror() # Mirror horizontally
        bend_ref_l_top.connect("o2", center_ref.ports[f"t_o1_{i}"])
        
        bend_ref_l_bot = c << s_bend
        bend_ref_l_bot.mirror() # Mirror horizontally
        bend_ref_l_bot.mirror(p1=(0, 0), p2=(1, 0)) # then Mirror vertically
        bend_ref_l_bot.connect("o2", center_ref.ports[f"b_o1_{i}"])

    return c

# Create an instance of the component
device = create_waisted_line_structure()

# This block executes when the script is run directly
if __name__ == "__main__":
    # FIX: Add the write_gds command to produce the final output file.
    device.write_gds("waisted_structure.gds")
    
    # The show() command is useful for visualization during development.
    device.show()