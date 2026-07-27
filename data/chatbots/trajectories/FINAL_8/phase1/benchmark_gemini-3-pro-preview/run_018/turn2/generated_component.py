import gdsfactory as gf

@gf.cell
def device_with_interaction_region():
    c = gf.Component("Directional_Coupler_With_Flat_Region")

    # ---------------------------------------------------------
    # Design Parameters
    # ---------------------------------------------------------
    total_length = 120.0
    
    # Split length into: Bend -> Straight -> Bend
    # Based on the visual aspect ratio, the flat interaction region 
    # covers about 1/3 to 1/2 of the device.
    interaction_length = 40.0
    bend_length = (total_length - interaction_length) / 2  # Result: 40.0 um
    
    # Vertical constraints (Footprint H=4um)
    # Using fine dimensions to fit 13 lines (5 center + 4 top + 4 bottom)
    line_width = 0.15
    line_gap = 0.15
    pitch = line_width + line_gap
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=line_width, layer=(1, 0))

    # ---------------------------------------------------------
    # 1. Center Bus (5 Straight Lines)
    # ---------------------------------------------------------
    num_center = 5
    # Calculate starting Y to center the group on Y=0
    center_y_start = -((num_center - 1) * pitch) / 2
    
    for i in range(num_center):
        y_pos = center_y_start + i * pitch
        wg = c << gf.components.straight(length=total_length, cross_section=xs)
        wg.movey(y_pos)

    # ---------------------------------------------------------
    # 2. Top Wing (4 Lines: Bend In -> Straight -> Bend Out)
    # ---------------------------------------------------------
    num_wing = 4
    coupling_gap = 0.2    # Distance between center and wing at closest point
    wing_drop = 0.8       # Vertical travel distance of the S-bend
    
    # Calculate Y positions
    # The bottom-most line of the top wing sits at:
    # (Top of center bus) + (Gap) + (Half width)
    y_center_top_edge = center_y_start + (num_center - 1) * pitch
    y_wing_inner_baseline = y_center_top_edge + coupling_gap + line_width
    
    for i in range(num_wing):
        # Y coordinate in the "Near" (Straight) region
        y_near = y_wing_inner_baseline + i * pitch
        # Y coordinate in the "Far" (Start/End) region
        y_far = y_near + wing_drop
        
        # Segment 1: Bend Down (Far -> Near)
        b1 = c << gf.components.bend_s(
            size=(bend_length, -wing_drop), 
            cross_section=xs
        )
        b1.move((0, y_far))
        
        # Segment 2: Straight Interaction Region (Flat)
        st = c << gf.components.straight(
            length=interaction_length, 
            cross_section=xs
        )
        st.connect("o1", b1.ports["o2"])
        
        # Segment 3: Bend Up (Near -> Far)
        b2 = c << gf.components.bend_s(
            size=(bend_length, wing_drop), 
            cross_section=xs
        )
        b2.connect("o1", st.ports["o2"])

    # ---------------------------------------------------------
    # 3. Bottom Wing (Mirror Logic)
    # ---------------------------------------------------------
    # The top-most line of the bottom wing sits at:
    # (Bottom of center bus) - (Gap) - (Half width)
    y_center_bot_edge = center_y_start
    y_wing_bot_inner_baseline = y_center_bot_edge - coupling_gap - line_width
    
    for i in range(num_wing):
        # Iterate downwards away from center
        y_near = y_wing_bot_inner_baseline - i * pitch
        y_far = y_near - wing_drop # Further away (more negative)
        
        # Segment 1: Bend Up (Far -> Near)
        # We start low and bend UP towards the center
        b1 = c << gf.components.bend_s(
            size=(bend_length, wing_drop), 
            cross_section=xs
        )
        b1.move((0, y_far))
        
        # Segment 2: Straight Interaction Region
        st = c << gf.components.straight(
            length=interaction_length, 
            cross_section=xs
        )
        st.connect("o1", b1.ports["o2"])
        
        # Segment 3: Bend Down (Near -> Far)
        # We start high and bend DOWN away from center
        b2 = c << gf.components.bend_s(
            size=(bend_length, -wing_drop), 
            cross_section=xs
        )
        b2.connect("o1", st.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate and show
    device = device_with_interaction_region()
    device.show()
    device.write_gds("refined_parametric_device.gds")