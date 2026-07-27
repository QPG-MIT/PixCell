import gdsfactory as gf

@gf.cell
def symmetric_coupler_final():
    """
    Creates a symmetric coupler matching the target image.
    Uses bend_s for smooth transitions and precise component assembly.
    
    Footprint: 120um x 4um
    """
    c = gf.Component("symmetric_coupler")

    # 1. Design Parameters
    width = 0.5        # Waveguide width
    gap = 0.2          # Coupling gap
    total_length = 120
    total_height = 4
    
    # Region lengths (Total must sum to 120)
    l_coupler = 60     # Length of the central coupling region
    l_sbend = 25       # Horizontal length of the S-bend transition
    l_straight = 5     # Length of the straight input/output ports
    # Verification: 5 + 25 + 60 + 25 + 5 = 120 um
    
    # 2. Calculate Vertical Offsets
    # Inner center (coupling region): centered at +/- (gap/2 + width/2)
    y_inner = (gap / 2) + (width / 2)  # 0.35 um
    # Outer center (ports): Flush with 4um boundary -> +/- (4/2 - width/2)
    y_outer = (total_height / 2) - (width / 2) # 1.75 um
    
    # Vertical distance the S-bend must bridge
    dy = y_outer - y_inner # 1.4 um

    # 3. Define Cross-Section
    xs = gf.cross_section.strip(width=width, layer=(1, 0))

    # 4. Create Sub-Components
    coupler_straight = gf.components.straight(length=l_coupler, cross_section=xs)
    sbend = gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    port_straight = gf.components.straight(length=l_straight, cross_section=xs)

    # 5. Assemble the Top Waveguide
    # Start with the central coupling section
    t_mid = c << coupler_straight
    t_mid.movey(y_inner)
    t_mid.movex(-l_coupler / 2) # Center it at x=0

    # Add left S-bend
    t_sbl = c << sbend
    t_sbl.connect("o2", t_mid.ports["o1"])

    # Add right S-bend
    t_sbr = c << sbend
    t_sbr.mirror_x()
    t_sbr.connect("o1", t_mid.ports["o2"])

    # Add port extensions
    t_port_l = c << port_straight
    t_port_l.connect("o2", t_sbl.ports["o1"])
    
    t_port_r = c << port_straight
    t_port_r.connect("o1", t_sbr.ports["o2"])

    # 6. Assemble the Bottom Waveguide (Mirror of Top)
    # We can add the whole top structure as a reference and mirror it, 
    # but for port consistency, we'll place them explicitly.
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

    # 7. Add External Ports
    c.add_port("o1", port=b_port_l.ports["o1"])
    c.add_port("o2", port=t_port_l.ports["o1"])
    c.add_port("o3", port=t_port_r.ports["o2"])
    c.add_port("o4", port=b_port_r.ports["o2"])

    return c

if __name__ == "__main__":
    device = symmetric_coupler_final()
    
    # Verification
    w, h = device.size_info.width, device.size_info.height
    print(f"Final Footprint: {w:.2f}um x {h:.2f}um")
    
    device.show()
    device.write_gds("symmetric_coupler.gds")