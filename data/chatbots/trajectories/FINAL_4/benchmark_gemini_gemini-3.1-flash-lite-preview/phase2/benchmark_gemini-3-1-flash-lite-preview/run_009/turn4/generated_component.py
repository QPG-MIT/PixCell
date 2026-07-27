import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    """
    Creates an adiabatic coupler with an 18um x 3um footprint.
    The waveguides curve toward each other, couple over a straight 
    section, and curve away.
    """
    c = gf.Component("adiabatic_coupler")
    
    # We define a cross-section with a smaller radius_min to allow 
    # for the compact s-bend transitions within our 18um footprint.
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius_min=0.1)
    
    # --- Top Waveguide ---
    # S-bend (down) -> Straight (coupling) -> S-bend (up)
    # The straight section is 9um, and each S-bend is 4.5um, totaling 18um.
    top_s1 = c << gf.components.bend_s(size=(4.5, -1.0), cross_section=xs)
    top_straight = c << gf.components.straight(length=9.0, cross_section=xs)
    top_s2 = c << gf.components.bend_s(size=(4.5, 1.0), cross_section=xs)
    
    # Position and connect
    top_s1.movey(1.25)
    top_straight.connect("o1", top_s1.ports["o2"])
    top_s2.connect("o1", top_straight.ports["o2"])
    
    # --- Bottom Waveguide ---
    # S-bend (up) -> Straight (coupling) -> S-bend (down)
    bot_s1 = c << gf.components.bend_s(size=(4.5, 1.0), cross_section=xs)
    bot_straight = c << gf.components.straight(length=9.0, cross_section=xs)
    bot_s2 = c << gf.components.bend_s(size=(4.5, -1.0), cross_section=xs)
    
    # Position and connect
    bot_s1.movey(-1.25)
    bot_straight.connect("o1", bot_s1.ports["o2"])
    bot_s2.connect("o1", bot_straight.ports["o2"])
    
    # Write the GDS file
    c.write_gds("adiabatic_coupler.gds")
    return c

if __name__ == "__main__":
    device = adiabatic_coupler()
    print("GDS file 'adiabatic_coupler.gds' successfully produced.")