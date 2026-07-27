import gdsfactory as gf

@gf.cell
def smooth_hourglass_coupler(length=120, dy=4):
    """
    Creates an hourglass coupler by joining two S-bends back-to-back.
    
    Args:
        length: Total device length.
        dy: Total vertical separation from the wide port to the center waist.
    """
    c = gf.Component("hourglass_coupler")
    xs = gf.cross_section.strip() # Standard cross-section

    # Each arm is composed of two S-bends.
    # The first bend takes the waveguide from the wide port to the center.
    # The second bend takes it from the center back to the wide port.
    
    # 1. Top Arm
    # Bend 1: Moves down from +dy/2 to 0
    top_s1 = c << gf.components.bend_s(size=(length/2, -dy/2), cross_section=xs)
    # Bend 2: Moves up from 0 to +dy/2
    top_s2 = c << gf.components.bend_s(size=(length/2, dy/2), cross_section=xs)
    
    top_s2.connect("o1", top_s1.ports["o2"])
    
    # 2. Bottom Arm
    # Bend 3: Moves up from -dy/2 to 0
    bot_s1 = c << gf.components.bend_s(size=(length/2, dy/2), cross_section=xs)
    # Bend 4: Moves down from 0 to -dy/2
    bot_s2 = c << gf.components.bend_s(size=(length/2, -dy/2), cross_section=xs)
    
    # Position the bottom arm starting point
    bot_s1.movey(-dy)
    bot_s2.movey(-dy)
    bot_s2.connect("o1", bot_s1.ports["o2"])

    # 3. Expose Ports
    c.add_port("o1", port=top_s1.ports["o1"])
    c.add_port("o2", port=bot_s1.ports["o1"])
    c.add_port("o3", port=top_s2.ports["o2"])
    c.add_port("o4", port=bot_s2.ports["o2"])

    return c

# Generate and save
device = smooth_hourglass_coupler()
device.write_gds("hourglass_coupler.gds")