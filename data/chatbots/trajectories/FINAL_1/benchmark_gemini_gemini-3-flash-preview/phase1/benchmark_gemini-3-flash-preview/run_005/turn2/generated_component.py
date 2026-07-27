import gdsfactory as gf

@gf.cell
def trident_coupler():
    """
    Recreates the trident coupler with improved proportions.
    Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component("trident_coupler")
    
    # --- Dimensions ---
    # Total Box: 40.0 x 1.7
    L_TOTAL = 40.0
    H_TOTAL = 1.7
    
    # Waveguide parameters
    w = 0.35          # Narrower width to match visual proportions
    w_tip = 0.01      # Sharper tip for the central taper
    gap_in = 0.12     # Gap between waveguides at the input side
    layer = (1, 0)
    
    # Cross sections for convenience
    xs = gf.cross_section.cross_section(width=w, layer=layer)
    
    # --- 1. Central Branch ---
    # Starts at x=0. Ends before the device ends (common for edge couplers).
    l_mid_straight = 10.0
    l_mid_taper = 26.0 # Long, sharp taper
    
    mid_s = c << gf.components.straight(length=l_mid_straight, cross_section=xs)
    mid_t = c << gf.components.taper(length=l_mid_taper, width1=w, width2=w_tip, layer=layer)
    mid_t.connect("o1", mid_s.ports["o2"])
    
    # --- 2. Side Branches ---
    # Calculations to hit exactly 1.7um total height:
    # Outer edge must be at y = +/- 0.85
    # Therefore, center of side waveguide at output = 0.85 - (w/2) = 0.675
    # Center of side waveguide at input = (w/2) + gap_in + (w/2) = 0.175 + 0.12 + 0.175 = 0.47
    y_in = 0.47
    y_out = 0.675
    dy = y_out - y_in # Vertical shift = 0.205
    
    # Longitudinal segments for side branches
    x_offset = 6.0    # Side branches start slightly "inboard" from the left edge
    l_side_s1 = 4.0   # Initial parallel straight section
    l_side_bend = 12.0 # More compact S-bend for a visible flare
    l_side_s2 = 18.0  # Long tail (6 + 4 + 12 + 18 = 40.0 total length)
    
    def add_side_branch(y_sign):
        # Create components
        s1 = gf.components.straight(length=l_side_s1, cross_section=xs)
        # Using bend_s for the smooth transition
        bend = gf.components.bend_s(size=(l_side_bend, y_sign * dy), cross_section=xs)
        s2 = gf.components.straight(length=l_side_s2, cross_section=xs)
        
        # Position start
        ref1 = c << s1
        ref1.move((x_offset, y_sign * y_in))
        
        # Connect subsequent parts
        ref_b = c << bend
        ref_b.connect("o1", ref1.ports["o2"])
        
        ref2 = c << s2
        ref2.connect("o1", ref_b.ports["o2"])
        
    add_side_branch(1)  # Top arm
    add_side_branch(-1) # Bottom arm
    
    return c

if __name__ == "__main__":
    device = trident_coupler()
    # Save the GDS
    device.write_gds("trident_coupler.gds")
    
    # Print verification
    print(f"Final Footprint: {device.xsize:.2f} um x {device.ysize:.2f} um")