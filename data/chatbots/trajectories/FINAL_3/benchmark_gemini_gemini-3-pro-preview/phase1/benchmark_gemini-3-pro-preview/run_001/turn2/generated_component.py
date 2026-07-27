import gdsfactory as gf

@gf.cell
def directional_coupler_s_bend():
    """
    A parametric directional coupler using S-bends.
    Parameters tuned to match visual proportions of the target image:
    - Thicker waveguides (1.0um)
    - Specific length distribution (Long coupler, moderate bends, short leads)
    - Matches 120um x 4um footprint constraint.
    """
    c = gf.Component()
    
    # --- Parameters ---
    # Overall dimensions
    total_length = 120.0
    total_height = 4.0 
    
    # Waveguide geometry derived from image analysis
    # The image shows waveguides are approx 1/4 of total height
    wg_width = 1.0
    
    # Gap analysis: Gap appears to be about 40% of the waveguide width
    gap_coupling = 0.4
    
    # Length partitioning to match image aspect ratios
    # Central flat region is the longest segment
    length_coupler = 50.0
    # Leads are very short stubs
    length_lead = 5.0
    # Remaining length assigned to S-bends
    # (120 - 50 - 2*5) / 2 = 30.0
    length_bend = (total_length - length_coupler - (2 * length_lead)) / 2
    
    # --- Vertical Position Calculations ---
    # Define Y-coordinates to satisfy the 4.0um height constraint
    
    # Input/Output Y positions (Outer edges at +/- 2.0)
    # Center y = Max_Y - Width/2
    y_io_top = (total_height / 2) - (wg_width / 2)   # 2.0 - 0.5 = 1.5
    y_io_bot = -y_io_top                             # -1.5
    
    # Coupling region Y positions (Separated by gap)
    # Center y = Gap/2 + Width/2
    y_coup_top = (gap_coupling / 2) + (wg_width / 2) # 0.2 + 0.5 = 0.7
    y_coup_bot = -y_coup_top                         # -0.7
    
    # Vertical shift required for the S-bends
    dy = y_io_top - y_coup_top # 1.5 - 0.7 = 0.8
    
    # --- Component Creation ---
    xs = gf.cross_section.cross_section(width=wg_width)

    # 1. Straight segments
    comp_lead = gf.components.straight(length=length_lead, cross_section=xs)
    comp_coupler = gf.components.straight(length=length_coupler, cross_section=xs)
    
    # 2. S-Bends
    # Bend down: moves from Outer to Inner (Input to Coupler)
    # Height change is negative
    bend_down = gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    
    # Bend up: moves from Inner to Outer (Coupler to Output)
    # Height change is positive
    bend_up = gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    
    # --- Assembly: Top Arm ---
    # Input Lead
    top_in = c << comp_lead
    top_in.move((0, y_io_top))
    
    # Bend Down (In to Coupler)
    top_b1 = c << bend_down
    top_b1.connect("o1", top_in.ports["o2"])
    
    # Coupler Straight
    top_c = c << comp_coupler
    top_c.connect("o1", top_b1.ports["o2"])
    
    # Bend Up (Coupler to Out)
    top_b2 = c << bend_up
    top_b2.connect("o1", top_c.ports["o2"])
    
    # Output Lead
    top_out = c << comp_lead
    top_out.connect("o1", top_b2.ports["o2"])
    
    # --- Assembly: Bottom Arm ---
    # Input Lead
    bot_in = c << comp_lead
    bot_in.move((0, y_io_bot))
    
    # Bend Up (In to Coupler) - using bend_up creates upward slope
    bot_b1 = c << bend_up
    bot_b1.connect("o1", bot_in.ports["o2"])
    
    # Coupler Straight
    bot_c = c << comp_coupler
    bot_c.connect("o1", bot_b1.ports["o2"])
    
    # Bend Down (Coupler to Out) - using bend_down creates downward slope
    bot_b2 = c << bend_down
    bot_b2.connect("o1", bot_c.ports["o2"])
    
    # Output Lead
    bot_out = c << comp_lead
    bot_out.connect("o1", bot_b2.ports["o2"])
    
    # --- Ports ---
    c.add_port("o1", port=top_in.ports["o1"])
    c.add_port("o2", port=bot_in.ports["o1"])
    c.add_port("o3", port=top_out.ports["o2"])
    c.add_port("o4", port=bot_out.ports["o2"])
    
    return c

# Generate and save
if __name__ == "__main__":
    device = directional_coupler_s_bend()
    device.write_gds("directional_coupler_s_bend.gds")
    device.show()