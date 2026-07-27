import gdsfactory as gf

@gf.cell
def create_symmetric_waveguide_structure():
    """
    Creates a symmetric structure with central straight lines, separating slabs,
    and outer lines that curve at the ends, all fitting within a defined footprint.
    """
    c = gf.Component("final_structure")

    # --- Parameters ---
    # Overall dimensions from footprint constraint
    total_width = 120.0
    
    # Define small vertical features to fit within the height constraint
    line_width = 0.1
    gap = 0.1
    pitch = line_width + gap

    # Slabs and spacing
    slab_height = 0.5
    slab_length = 70.0  # MODIFIED: Slabs are now shorter than the outer straight sections.
    gap_center_to_slab = 0.05  # MODIFIED: Reduced gap to fit height constraint.
    gap_slab_to_outer = 0.05  # MODIFIED: Reduced gap to fit height constraint.
    
    # Number of lines in each group
    num_lines_center = 5  # MODIFIED: Changed from 4 to 5.
    num_lines_outer = 5   # MODIFIED: Changed from 4 to 5.
    
    # Parameters for the outer curved lines
    bend_radius = 200
    bend_angle = 2.5

    # --- Component Assembly ---
    
    xs = gf.cross_section.cross_section(width=line_width)

    # --- Calculations for Geometry ---
    # Create a temporary bend to measure its horizontal extent (dx)
    temp_bend = gf.components.bend_euler(radius=bend_radius, angle=bend_angle)
    bend_dx = temp_bend.dx
    
    # The length of the inner straight sections for the outer lines
    len_inner_section = total_width - 2 * bend_dx

    # 1. Central group of 5 straight lines
    # This group is centered around y=0
    y_start_center = -(num_lines_center - 1) / 2 * pitch
    for i in range(num_lines_center):
        y_pos = y_start_center + i * pitch
        # Create a straight line component
        straight_line = gf.components.straight(length=total_width, cross_section=xs)
        # Add a reference to the main component and center it
        s_ref = c << straight_line
        s_ref.center = (0, y_pos)

    # Calculate the top edge of the central group
    y_max_center = y_start_center + (num_lines_center - 1) * pitch + line_width / 2

    # 2. Top and Bottom Slabs
    # Use the new shorter slab_length
    slab = gf.components.rectangle(size=(slab_length, slab_height))
    
    # Position the top slab
    y_slab_center = y_max_center + gap_center_to_slab + slab_height / 2
    slab_top_ref = c << slab
    slab_top_ref.y = y_slab_center # x is already 0 due to default centering
    
    # Position the bottom slab
    slab_bot_ref = c << slab
    slab_bot_ref.y = -y_slab_center

    # 3. Outer curved groups (Top and Bottom)
    
    # First, create a single curved line as a reusable, centered component
    @gf.cell
    def single_curved_line():
        line_component = gf.Component()
        straight_section = gf.components.straight(length=len_inner_section, cross_section=xs)
        bend_section = gf.components.bend_euler(radius=bend_radius, angle=bend_angle, cross_section=xs)
        
        s_ref = line_component << straight_section
        s_ref.center = (0, 0)
        
        bend_right_ref = line_component << bend_section
        bend_left_ref = line_component << bend_section
        bend_left_ref.mirror() # Mirror across y-axis for the left-side bend
        
        bend_right_ref.connect("o1", s_ref.ports["o2"])
        bend_left_ref.connect("o1", s_ref.ports["o1"])
        
        return line_component

    # Create a component for the top group of 5 curved lines
    top_outer_group = gf.Component("top_curved_lines")
    for i in range(num_lines_outer):
        y_offset = i * pitch
        line_ref = top_outer_group << single_curved_line()
        line_ref.y = y_offset

    # Calculate the starting y-position for the center of the bottom-most line in the top group
    y_max_slab = y_slab_center + slab_height / 2
    y_start_outer_group = y_max_slab + gap_slab_to_outer + line_width / 2

    # Add the top group and a mirrored bottom group to the main component
    top_ref = c << top_outer_group
    top_ref.y = y_start_outer_group
    
    bot_ref = c << top_outer_group
    bot_ref.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across the x-axis to flip curves down
    bot_ref.y = -y_start_outer_group

    return c

# --- Main execution block ---
if __name__ == "__main__":
    device = create_symmetric_waveguide_structure()
    
    # Write the component to a GDS file
    device.write_gds("final_structure.gds")
    
    # Show the component in the KLayout viewer for verification
    device.show()