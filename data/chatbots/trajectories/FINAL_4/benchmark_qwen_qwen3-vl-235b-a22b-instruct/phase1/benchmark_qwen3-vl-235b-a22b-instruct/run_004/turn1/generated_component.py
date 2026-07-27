import gdsfactory as gf

@gf.cell
def s_bend_coupler():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create first S-bend waveguide
    s_bend1 = c << gf.components.bend_s(size=(18, 3), cross_section=xs)
    s_bend1.move((0, 0))
    
    # Create second S-bend waveguide (mirror of first)
    s_bend2 = c << gf.components.bend_s(size=(18, 3), cross_section=xs)
    s_bend2.move((0, -0.5))  # Position below first with small gap
    
    # Add ports for connectivity
    c.add_port("o1", port=s_bend1.ports["o1"])
    c.add_port("o2", port=s_bend1.ports["o2"])
    c.add_port("o3", port=s_bend2.ports["o1"])
    c.add_port("o4", port=s_bend2.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_coupler()
device.write_gds("s_bend_coupler.gds")