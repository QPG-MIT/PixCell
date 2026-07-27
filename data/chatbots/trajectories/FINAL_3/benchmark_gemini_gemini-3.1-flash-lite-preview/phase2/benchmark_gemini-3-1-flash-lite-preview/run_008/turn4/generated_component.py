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
    # Length = 40, Gap = 0.5um (Coupler ports: o1=BL, o2=BR, o3=TL, o4=TR)
    coupler = c << gf.components.coupler_straight(length=40, gap=0.5, cross_section=xs)
    
    # 2. Add S-bends to flare the waveguides outward.
    # The coupler ports are at y = ±0.25 (since gap = 0.5).
    # We want to flare to y = ±2.0. The total displacement is 1.75um.
    
    # Left side flares
    bend_tl = c << gf.components.bend_s(size=(20, -1.75), cross_section=xs)
    bend_bl = c << gf.components.bend_s(size=(20, 1.75), cross_section=xs)
    
    # Right side flares
    bend_tr = c << gf.components.bend_s(size=(20, 1.75), cross_section=xs)
    bend_br = c << gf.components.bend_s(size=(20, -1.75), cross_section=xs)
    
    # 3. Connect the components carefully to avoid "X" crossing
    # Assuming standard GDSFactory coupler port convention: 
    # o1=Bottom-Left, o2=Bottom-Right, o3=Top-Left, o4=Top-Right
    
    # Left connections: TL to TL, BL to BL
    bend_tl.connect("o2", coupler.ports["o3"])
    bend_bl.connect("o2", coupler.ports["o1"])
    
    # Right connections: TR to TR, BR to BR
    bend_tr.connect("o1", coupler.ports["o4"])
    bend_br.connect("o1", coupler.ports["o2"])
    
    # 4. Add external ports
    c.add_port("W1", port=bend_tl.ports["o1"])
    c.add_port("W0", port=bend_bl.ports["o1"])
    c.add_port("E1", port=bend_tr.ports["o2"])
    c.add_port("E0", port=bend_br.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = flared_coupler_device()
    # Save the GDS file
    device.write_gds("flared_coupler.gds")
    # Open in KLayout
    device.show()