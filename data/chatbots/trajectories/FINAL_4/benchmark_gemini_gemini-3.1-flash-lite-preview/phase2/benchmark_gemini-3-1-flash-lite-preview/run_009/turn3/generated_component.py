import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    """
    Creates an adiabatic coupler using two connected S-bends to ensure 
    a smooth, continuous transition within the 18um x 3um footprint.
    """
    c = gf.Component("adiabatic_coupler")
    
    # Define a standard waveguide cross-section (width=0.5um)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Top waveguide:
    # 1. Bend S down 1um over 9um (from y=1.25 to y=0.25)
    # 2. Bend S up 1um over 9um (from y=0.25 to y=1.25)
    top_s1 = c << gf.components.bend_s(size=(9, -1.0), cross_section=xs)
    top_s2 = c << gf.components.bend_s(size=(9, 1.0), cross_section=xs)
    
    # Position the top waveguide
    top_s1.movey(1.25)
    top_s2.connect("o1", top_s1.ports["o2"])
    
    # Bottom waveguide:
    # 1. Bend S up 1um over 9um (from y=-1.25 to y=-0.25)
    # 2. Bend S down 1um over 9um (from y=-0.25 to y=-1.25)
    bot_s1 = c << gf.components.bend_s(size=(9, 1.0), cross_section=xs)
    bot_s2 = c << gf.components.bend_s(size=(9, -1.0), cross_section=xs)
    
    # Position the bottom waveguide
    bot_s1.movey(-1.25)
    bot_s2.connect("o1", bot_s1.ports["o2"])
    
    # Write the GDS file
    c.write_gds("adiabatic_coupler.gds")
    return c

if __name__ == "__main__":
    device = adiabatic_coupler()
    print("GDS file 'adiabatic_coupler.gds' successfully produced.")