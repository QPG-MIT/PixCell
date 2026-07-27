import gdsfactory as gf

@gf.cell
def inverse_taper_coupler():
    """
    Creates an inverse taper edge coupler based on the target geometry.
    
    Structure:
    1. Central Taper: A linear taper from 0.6um to 0.05um.
    2. Outer Arms: 
       - Start as parallel straight waveguides.
       - S-bend inwards to capture the mode.
       - Merge at the output to form a single solid waveguide.
    """
    c = gf.Component()
    
    # --- Dimensions & Constraints ---
    # Total footprint constraint: [40.0, 1.7]
    total_length = 40.0
    
    # Widths selected to maximize usage of the 1.7um height limit
    # Layout: [Arm 0.4] [Gap 0.15] [Center 0.6] [Gap 0.15] [Arm 0.4]
    # Total Y span = 0.4 + 0.15 + 0.6 + 0.15 + 0.4 = 1.7um
    w_center = 0.6
    w_arm = 0.4
    w_tip = 0.05
    gap_in = 0.15
    
    # Length Segmentation
    len_straight_in = 12.0  # Parallel section at input
    len_sbend = 18.0        # Converging section
    len_straight_out = 10.0 # Merged output section
    len_taper = 27.0        # Ends just as arms converge tight
    
    # Layer definition
    layer = (1, 0)
    xs_arm = gf.cross_section.cross_section(width=w_arm, layer=layer)
    
    # --- Y-Coordinate Calculations ---
    # Input Y positions (centered)
    # Center of arm = (Half Center Width) + Gap + (Half Arm Width)
    y_arm_in_center = (w_center / 2) + gap_in + (w_arm / 2)  # 0.3 + 0.15 + 0.2 = 0.65
    
    # Output Y positions (merged)
    # We want the arms to overlap slightly to form a solid block.
    # Overlap = 0.1um. Inner edge at -0.05um.
    overlap = 0.1
    y_arm_out_center = (w_arm / 2) - (overlap / 2) # 0.2 - 0.05 = 0.15

    # --- 1. Central Taper ---
    # Placed at origin (0,0)
    taper = c << gf.components.taper(
        length=len_taper,
        width1=w_center,
        width2=w_tip,
        layer=layer
    )

    # --- 2. Top Arm Construction ---
    # Segment 1: Straight
    t_s1 = c << gf.components.straight(length=len_straight_in, cross_section=xs_arm)
    t_s1.move((0, y_arm_in_center))
    
    # Segment 2: S-Bend (Converging)
    dy_top = y_arm_out_center - y_arm_in_center
    t_bend = c << gf.components.bend_s(
        size=(len_sbend, dy_top),
        cross_section=xs_arm
    )
    t_bend.connect("o1", t_s1.ports["o2"])
    
    # Segment 3: Straight (Merged Output)
    t_s3 = c << gf.components.straight(length=len_straight_out, cross_section=xs_arm)
    t_s3.connect("o1", t_bend.ports["o2"])
    
    # --- 3. Bottom Arm Construction ---
    # Segment 1: Straight
    b_s1 = c << gf.components.straight(length=len_straight_in, cross_section=xs_arm)
    b_s1.move((0, -y_arm_in_center))
    
    # Segment 2: S-Bend (Converging Upwards)
    dy_bot = -y_arm_out_center - (-y_arm_in_center)
    b_bend = c << gf.components.bend_s(
        size=(len_sbend, dy_bot),
        cross_section=xs_arm
    )
    b_bend.connect("o1", b_s1.ports["o2"])
    
    # Segment 3: Straight (Merged Output)
    b_s3 = c << gf.components.straight(length=len_straight_out, cross_section=xs_arm)
    b_s3.connect("o1", b_bend.ports["o2"])

    # --- 4. Ports ---
    c.add_port("o1", port=taper.ports["o1"])
    
    # Calculate effective output width (Sum of arms - overlap)
    output_width = (w_arm * 2) - overlap
    c.add_port(
        "o2",
        center=(total_length, 0),
        width=output_width,
        orientation=0,
        layer=layer
    )

    return c

if __name__ == "__main__":
    device = inverse_taper_coupler()
    device.write_gds("inverse_taper_coupler.gds")
    device.show()