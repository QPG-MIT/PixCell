import gdsfactory as gf

@gf.cell
def symmetric_coupler_refined():
    """
    Refined symmetric coupler matching the target image proportions.
    
    Footprint: 120um x 4um
    - Longer coupling region (80um)
    - Thinner waveguides (0.4um)
    - Sharper S-bend transitions
    """
    c = gf.Component("symmetric_coupler")

    # 1. Design Parameters
    width = 0.4        # Thinner waveguide width for a better aspect ratio
    gap = 0.2          # Coupling gap in the center
    total_length = 120
    total_height = 4
    
    # Horizontal segment lengths (Total must sum to 120um)
    l_coupler = 80     # Long central coupling region
    l_sbend = 15       # Compact horizontal length for transitions
    l_straight = 5     # Input/Output port extensions
    # Check: 5 + 15 + 80 + 15 + 5 = 120 um
    
    # 2. Vertical Calculations
    # Port centers at the 4um boundary: +/- (total_height/2 - width/2)
    y_outer = (total_height / 2) - (width / 2)  # 1.8 um
    # Coupling centers: +/- (gap/2 + width/2)
    y_inner = (gap / 2) + (width / 2)           # 0.3 um
    # Vertical distance to bridge
    dy = y_outer - y_inner                      # 1.5 um

    # 3. Define Cross-Section
    xs = gf.cross_section.strip(width=width, layer=(1, 0))

    # 4. Create Components
    coupler_straight = gf.components.straight(length=l_coupler, cross_section=xs)
    sbend = gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    port_straight = gf.components.straight(length=l_straight, cross_section=xs)

    # 5. Assemble Top Waveguide
    t_mid = c << coupler_straight
    t_mid.movey(y_inner)
    t_mid.movex(-l_coupler / 2) # Center horizontally

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

    # 7. Define Ports
    c.add_port("o1", port=b_port_l.ports["o1"])
    c.add_port("o2", port=t_port_l.ports["o1"])
    c.add_port("o3", port=t_port_r.ports["o2"])
    c.add_port("o4", port=b_port_r.ports["o2"])

    return c

if __name__ == "__main__":
    device = symmetric_coupler_refined()
    
    # Final check on footprint
    w, h = device.size_info.width, device.size_info.height
    print(f"Resulting Footprint: {w:.1f}um x {h:.1f}um")
    
    device.show()
    device.write_gds("symmetric_coupler_refined.gds")