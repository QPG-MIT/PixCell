import gdsfactory as gf

@gf.cell
def symmetric_coupler_refined():
    """
    Refined symmetric coupler matching the target image.
    Includes a central parallel coupling region and smooth S-bends
    to fill the 18um x 3um footprint.
    """
    c = gf.Component("symmetric_coupler_refined")
    
    # Footprint constraints
    total_length = 18.0
    total_height = 3.0
    
    # Design parameters
    width = 0.7          # Adjusted for visual weight
    gap = 0.2            # Gap between waveguides in the coupling region
    coupling_len = 3.0   # Length of the parallel central section
    
    # Calculated dimensions
    # Length of each of the 4 S-bends
    sbend_len = (total_length - coupling_len) / 2
    
    # Vertical centers
    # At edges: center is half-width away from the 1.5um boundary
    y_edge = (total_height / 2) - (width / 2) 
    # At center: center is half-width + half-gap away from the midline
    y_mid = (gap / 2) + (width / 2)
    # Vertical displacement for the S-bend
    dy = y_mid - y_edge
    
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    
    # --- Top Arm Construction ---
    # Left S-bend
    t_sbend_l = c << gf.components.bend_s(size=(sbend_len, dy), cross_section=xs)
    t_sbend_l.movey(y_edge)
    
    # Central coupling straight
    t_mid = c << gf.components.straight(length=coupling_len, cross_section=xs)
    t_mid.connect("o1", t_sbend_l.ports["o2"])
    
    # Right S-bend
    t_sbend_r = c << gf.components.bend_s(size=(sbend_len, -dy), cross_section=xs)
    t_sbend_r.connect("o1", t_mid.ports["o2"])
    
    # --- Bottom Arm Construction ---
    # Mirrored version of the top arm
    b_sbend_l = c << gf.components.bend_s(size=(sbend_len, -dy), cross_section=xs)
    b_sbend_l.movey(-y_edge)
    
    b_mid = c << gf.components.straight(length=coupling_len, cross_section=xs)
    b_mid.connect("o1", b_sbend_l.ports["o2"])
    
    b_sbend_r = c << gf.components.bend_s(size=(sbend_len, dy), cross_section=xs)
    b_sbend_r.connect("o1", b_mid.ports["o2"])
    
    # Center the component at (0,0)
    c.movex(-total_length / 2)
    
    # Add external ports
    c.add_port("o1", port=t_sbend_l.ports["o1"])
    c.add_port("o2", port=b_sbend_l.ports["o1"])
    c.add_port("o3", port=t_sbend_r.ports["o2"])
    c.add_port("o4", port=b_sbend_r.ports["o2"])

    return c

if __name__ == "__main__":
    component = symmetric_coupler_refined()
    
    # Final check: Print dimensions to ensure footprint is exactly 18x3
    print(f"Final Dimensions: {component.dxsize:.2f} x {component.dysize:.2f} um")
    
    component.write_gds("symmetric_coupler_v3.gds")
    component.show()