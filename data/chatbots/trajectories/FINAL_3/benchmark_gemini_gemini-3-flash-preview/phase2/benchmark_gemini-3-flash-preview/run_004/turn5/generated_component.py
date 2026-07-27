import gdsfactory as gf

@gf.cell
def symmetric_coupler_final():
    """
    Final refinement of the symmetric coupler matching target image proportions.
    
    Footprint: 120um x 4um
    - Central coupling region: 60um
    - Smooth S-bend transitions: 25um horizontal reach
    - Waveguide width: 0.5um
    - Gap: 0.2um
    """
    c = gf.Component("symmetric_coupler")

    # 1. Design Parameters
    width = 0.5        # Increased width for better aspect ratio
    gap = 0.2          # Coupling gap
    total_length = 120
    total_height = 4   # Fixed footprint constraint
    
    # Horizontal segment lengths (Total: 5 + 25 + 60 + 25 + 5 = 120um)
    l_coupler = 60     # Proportional central region
    l_sbend = 25       # Increased length for a smoother transition
    l_straight = 5     # Short lead-ins for ports
    
    # 2. Vertical Calculations
    # To keep total footprint height at 4um, edges must be at +/- 2.0
    # Center of outer waveguides: +/- (2.0 - width/2)
    y_outer = (total_height / 2) - (width / 2)  # 1.75 um
    
    # Center of waveguides in the coupling region: +/- (gap/2 + width/2)
    y_inner = (gap / 2) + (width / 2)           # 0.35 um
    
    # Vertical distance to bridge
    dy = y_outer - y_inner                      # 1.4 um

    # 3. Define Cross-Section
    xs = gf.cross_section.strip(width=width, layer=(1, 0))

    # 4. Create Component Primitives
    coupler_straight = gf.components.straight(length=l_coupler, cross_section=xs)
    sbend = gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    port_straight = gf.components.straight(length=l_straight, cross_section=xs)

    # 5. Assemble Top Waveguide
    t_mid = c << coupler_straight
    t_mid.movey(y_inner)
    t_mid.movex(-l_coupler / 2)

    t_sbl = c << sbend
    t_sbl.connect("o2", t_mid.ports["o1"])

    t_sbr = c << sbend
    t_sbr.mirror_x()
    t_sbr.connect("o1", t_mid.ports["o2"])

    t_port_l = c << port_straight
    t_port_l.connect("o2", t_sbl.ports["o1"])
    t_port_r = c << port_straight
    t_port_r.connect("o1", t_sbr.ports["o2"])

    # 6. Assemble Bottom Waveguide
    b_mid = c << coupler_straight
    b_mid.movey(-y_inner)
    b_mid.movex(-l_coupler / 2)

    b_sbl = c << sbend
    b_sbl.mirror_y()
    b_sbl.connect("o2", b_mid.ports["o1"])

    b_sbr = c << sbend
    b_sbr.mirror_y()
    b_sbr.mirror_x()
    b_sbr.connect("o1", b_mid.ports["o2"])

    b_port_l = c << port_straight
    b_port_l.connect("o2", b_sbl.ports["o1"])
    b_port_r = c << port_straight
    b_port_r.connect("o1", b_sbr.ports["o2"])

    # 7. Expose Ports
    c.add_port("o1", port=b_port_l.ports["o1"])
    c.add_port("o2", port=t_port_l.ports["o1"])
    c.add_port("o3", port=t_port_r.ports["o2"])
    c.add_port("o4", port=b_port_r.ports["o2"])

    return c

if __name__ == "__main__":
    device = symmetric_coupler_final()
    
    # Verification
    w, h = device.size_info.width, device.size_info.height
    print(f"Final Footprint: {w:.1f}um x {h:.1f}um")
    
    device.show()
    device.write_gds("symmetric_coupler_final.gds")