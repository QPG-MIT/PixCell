import gdsfactory as gf

@gf.cell
def flared_coupler_device():
    """
    Constructs an adiabatic coupler with a straight coupling section 
    and S-bend flares at the inputs/outputs.
    """
    c = gf.Component("flared_coupler")
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # 1. Center coupling section: two parallel waveguides with a gap
    # coupler_straight ports: o1=Left-Bottom, o2=Right-Bottom, o3=Left-Top, o4=Right-Top
    coupler = c << gf.components.coupler_straight(length=40, gap=0.5, cross_section=xs)
    
    # 2. Add S-bends to flare the waveguides outward.
    # Total displacement = 1.75um (target y = ±2.0, coupler y = ±0.25).
    # Left side flares (dx = -20)
    bend_tl = c << gf.components.bend_s(size=(-20, 1.75), cross_section=xs)
    bend_bl = c << gf.components.bend_s(size=(-20, -1.75), cross_section=xs)
    
    # Right side flares (dx = 20)
    bend_tr = c << gf.components.bend_s(size=(20, 1.75), cross_section=xs)
    bend_br = c << gf.components.bend_s(size=(20, -1.75), cross_section=xs)
    
    # 3. Connect the components
    # Connect Left side
    bend_tl.connect("o1", coupler.ports["o3"])
    bend_bl.connect("o1", coupler.ports["o1"])
    
    # Connect Right side
    bend_tr.connect("o1", coupler.ports["o4"])
    bend_br.connect("o1", coupler.ports["o2"])
    
    # 4. Add external ports (using the free ends o2 of the S-bends)
    c.add_port("W1", port=bend_tl.ports["o2"])
    c.add_port("W0", port=bend_bl.ports["o2"])
    c.add_port("E1", port=bend_tr.ports["o2"])
    c.add_port("E0", port=bend_br.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = flared_coupler_device()
    # Save the GDS file
    device.write_gds("flared_coupler.gds")
    # Open in KLayout
    device.show()