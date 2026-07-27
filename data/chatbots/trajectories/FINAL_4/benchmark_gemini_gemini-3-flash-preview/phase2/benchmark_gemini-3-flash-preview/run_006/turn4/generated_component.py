import gdsfactory as gf

@gf.cell
def symmetric_coupler_v5():
    """
    Symmetric coupler matching the target image proportions.
    
    Fixes the ValueError by:
    1. Reducing the minimum radius constraint in the cross-section.
    2. Slightly lengthening the S-bends to ensure smoother curves.
    
    Footprint: 18um x 3um.
    """
    c = gf.Component("symmetric_coupler_v5")
    
    # Footprint constraints
    total_length = 18.0
    total_height = 3.0
    
    # Design parameters refined for visual matching
    width = 0.5          # Thinner waveguides for appropriate visual weight
    gap = 0.1            # Narrow gap for the central coupling region
    coupling_len = 2.0   # Shorter central section to allow for longer, smoother S-bends
    
    # Calculated dimensions for S-bends
    # With total_length=18 and coupling_len=2, each S-bend is 8um long.
    sbend_len = (total_length - coupling_len) / 2
    
    # Vertical center positions
    # At edges: center is 1.25um from midline (for 0.5um width in 3um height)
    y_edge = (total_height / 2) - (width / 2) 
    # At center: center is 0.3um from midline (gap/2 + width/2)
    y_mid = (gap / 2) + (width / 2)
    # The vertical shift required for the S-bend
    dy = y_mid - y_edge
    
    layer = (1, 0)
    # Explicitly set radius=5.0 to bypass the default 10.0um minimum radius error
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius=5.0)
    
    # --- Top Arm Construction ---
    # Left S-bend: transitions from outer edge down to coupling gap
    t_sbend_l = c << gf.components.bend_s(size=(sbend_len, dy), cross_section=xs)
    t_sbend_l.movey(y_edge)
    
    # Central coupling straight
    t_mid = c << gf.components.straight(length=coupling_len, cross_section=xs)
    t_mid.connect("o1", t_sbend_l.ports["o2"])
    
    # Right S-bend: transitions from coupling gap back to outer edge
    t_sbend_r = c << gf.components.bend_s(size=(sbend_len, -dy), cross_section=xs)
    t_sbend_r.connect("o1", t_mid.ports["o2"])
    
    # --- Bottom Arm Construction (Mirrored) ---
    # Left S-bend: transitions from outer edge up to coupling gap
    b_sbend_l = c << gf.components.bend_s(size=(sbend_len, -dy), cross_section=xs)
    b_sbend_l.movey(-y_edge)
    
    # Central coupling straight
    b_mid = c << gf.components.straight(length=coupling_len, cross_section=xs)
    b_mid.connect("o1", b_sbend_l.ports["o2"])
    
    # Right S-bend: transitions from coupling gap back to outer edge
    b_sbend_r = c << gf.components.bend_s(size=(sbend_len, dy), cross_section=xs)
    b_sbend_r.connect("o1", b_mid.ports["o2"])
    
    # Center the entire component at (0,0)
    c.movex(-total_length / 2)
    
    # Expose external ports
    c.add_port("o1", port=t_sbend_l.ports["o1"])
    c.add_port("o2", port=b_sbend_l.ports["o1"])
    c.add_port("o3", port=t_sbend_r.ports["o2"])
    c.add_port("o4", port=b_sbend_r.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    component = symmetric_coupler_v5()
    
    # Print final dimensions to verify footprint
    print(f"Final Component Dimensions: {component.dxsize:.2f} x {component.dysize:.2f} um")
    
    # Export and visualize
    component.write_gds("symmetric_coupler_v5.gds")
    component.show()