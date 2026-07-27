import gdsfactory as gf

@gf.cell
def smooth_hourglass_coupler(length=120, dy=4, gap=0.2):
    """
    Creates an hourglass coupler by joining two S-bends and a straight segment.
    
    Args:
        length: Total device length.
        dy: Total vertical separation between the input ports.
        gap: Gap between waveguides in the middle section.
    """
    c = gf.Component("hourglass_coupler")
    xs = gf.cross_section.strip() # Standard cross-section
    
    # Calculate dimensions for the segments
    # Total length = 2 * L_s + L_straight
    # Using 40um for the waist length, leaving 80um for the two S-bends (40um each)
    l_straight = 40
    l_s = (length - l_straight) / 2
    
    # Vertical shift needed for each S-bend to reach the desired gap
    # Each S-bend moves from the edge (dy/2) to the center (gap/2)
    dy_shift = (dy - gap) / 2
    
    # --- Top Arm ---
    # S-bend down to the waist
    s1 = c << gf.components.bend_s(size=(l_s, -dy_shift), cross_section=xs)
    s1.movey(dy / 2)
    
    # Straight waist section
    st = c << gf.components.straight(length=l_straight, cross_section=xs)
    st.connect("o1", s1.ports["o2"])
    
    # S-bend back up
    s2 = c << gf.components.bend_s(size=(l_s, dy_shift), cross_section=xs)
    s2.connect("o1", st.ports["o2"])
    
    # --- Bottom Arm ---
    # S-bend up to the waist
    s3 = c << gf.components.bend_s(size=(l_s, dy_shift), cross_section=xs)
    s3.movey(-dy / 2)
    
    # Straight waist section
    st2 = c << gf.components.straight(length=l_straight, cross_section=xs)
    st2.connect("o1", s3.ports["o2"])
    
    # S-bend back down
    s4 = c << gf.components.bend_s(size=(l_s, -dy_shift), cross_section=xs)
    s4.connect("o1", st2.ports["o2"])

    # Expose Ports
    c.add_port("o1", port=s1.ports["o1"])
    c.add_port("o2", port=s3.ports["o1"])
    c.add_port("o3", port=s2.ports["o2"])
    c.add_port("o4", port=s4.ports["o2"])

    return c

# Generate and save
device = smooth_hourglass_coupler()
device.write_gds("hourglass_coupler.gds")