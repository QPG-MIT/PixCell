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
    # Length = 40, Gap = 0.5um
    coupler = c << gf.components.coupler_straight(length=40, gap=0.5, cross_section=xs)
    
    # 2. Add S-bends to flare the waveguides outward.
    # The coupler ports are at y = ±0.25 (since gap = 0.5).
    # We want to flare to y = ±2.0. The total displacement is 1.75um.
    # Size = (dx, dy)
    
    # Left side flares
    bend_tl = c << gf.components.bend_s(size=(20, -1.75), cross_section=xs)
    bend_bl = c << gf.components.bend_s(size=(20, 1.75), cross_section=xs)
    
    # Right side flares
    bend_tr = c << gf.components.bend_s(size=(20, 1.75), cross_section=xs)
    bend_br = c << gf.components.bend_s(size=(20, -1.75), cross_section=xs)
    
    # 3. Connect the components
    # coupler.ports: o1 (top-left), o2 (top-right), o3 (bottom-left), o4 (bottom-right)
    
    # Left connections
    bend_tl.connect("o2", coupler.ports["o1"])
    bend_bl.connect("o2", coupler.ports["o3"])
    
    # Right connections
    bend_tr.connect("o1", coupler.ports["o2"])
    bend_br.connect("o1", coupler.ports["o4"])
    
    return c

if __name__ == "__main__":
    device = flared_coupler_device()
    # Save the GDS file
    device.write_gds("flared_coupler.gds")
    # Open in KLayout
    device.show()