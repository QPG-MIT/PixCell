import gdsfactory as gf

@gf.cell
def trident_coupler():
    """
    Recreates the trident coupler geometry based on the image and footprint.
    Footprint Constraint: 40.0 um x 1.7 um
    """
    c = gf.Component("trident_coupler")

    # --- Design Parameters ---
    total_width = 40.0
    total_height = 1.7
    
    # Geometry Specs
    layer = (1, 0)
    w_mid = 0.5      # Starting width of center waveguide
    w_side = 0.4     # Width of side waveguides
    w_tip = 0.02     # Tip width of the center taper
    gap_in = 0.1     # Gap between waveguides at input
    
    # --- 1. Central Branch ---
    # Positioned at x=0 to define the left edge of the footprint.
    l_mid_straight = 10.0
    l_mid_taper = 20.0
    
    xs_mid = gf.cross_section.cross_section(width=w_mid, layer=layer)
    mid_s = c << gf.components.straight(length=l_mid_straight, cross_section=xs_mid)
    mid_t = c << gf.components.taper(length=l_mid_taper, width1=w_mid, width2=w_tip, layer=layer)
    mid_t.connect("o1", mid_s.ports["o2"])
    
    # --- 2. Side Branches ---
    # These define the right edge (ending at x=40) and total height (1.7um).
    # Math for 1.7um height:
    # Outer edge = 0.85 -> Center y at output = 0.85 - (w_side/2) = 0.65
    # Center y at input = (w_mid/2) + gap_in + (w_side/2) = 0.25 + 0.1 + 0.2 = 0.55
    # dy (S-bend vertical shift) = 0.65 - 0.55 = 0.1
    
    y_in = 0.55
    dy = 0.1
    
    # Longitudinal segments to reach x=40 (Side branches start at x=5)
    x_start_side = 5.0
    l_side_s1 = 5.0
    l_side_bend = 20.0
    l_side_s2 = 10.0  # 5 (start) + 5 + 20 + 10 = 40 (end)
    
    xs_side = gf.cross_section.cross_section(width=w_side, layer=layer)
    
    # Top Branch Assembly
    t_s1 = gf.components.straight(length=l_side_s1, cross_section=xs_side)
    t_bend = gf.components.bend_s(size=(l_side_bend, dy), cross_section=xs_side)
    t_s2 = gf.components.straight(length=l_side_s2, cross_section=xs_side)
    
    ref_t1 = c << t_s1
    ref_t1.move((x_start_side, y_in))
    ref_tb = c << t_bend
    ref_tb.connect("o1", ref_t1.ports["o2"])
    ref_t2 = c << t_s2
    ref_t2.connect("o1", ref_tb.ports["o2"])
    
    # Bottom Branch Assembly (Symmetric)
    b_s1 = gf.components.straight(length=l_side_s1, cross_section=xs_side)
    b_bend = gf.components.bend_s(size=(l_side_bend, -dy), cross_section=xs_side)
    b_s2 = gf.components.straight(length=l_side_s2, cross_section=xs_side)
    
    ref_b1 = c << b_s1
    ref_b1.move((x_start_side, -y_in))
    ref_bb = c << b_bend
    ref_bb.connect("o1", ref_b1.ports["o2"])
    ref_b2 = c << b_s2
    ref_b2.connect("o1", ref_bb.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    device = trident_coupler()
    
    # Explicitly write the GDS file
    device.write_gds("component.gds")
    
    # Verification print
    print(f"Device Bounding Box: {device.xsize:.2f} x {device.ysize:.2f} um")