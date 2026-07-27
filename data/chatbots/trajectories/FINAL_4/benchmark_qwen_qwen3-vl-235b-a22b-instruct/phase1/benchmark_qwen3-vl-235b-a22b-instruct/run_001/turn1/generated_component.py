import gdsfactory as gf

@gf.cell
def s_bend_coupler():
    c = gf.Component()
    
    # Define cross-section (default waveguide width)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the first S-bend
    s_bend1 = c << gf.components.bend_s(size=(18, 3), cross_section=xs)
    
    # Create the second S-bend (parallel to the first)
    # We need to offset it vertically to create the parallel waveguide
    # The gap between waveguides should be small, let's use 0.2μm as a typical gap
    s_bend2 = c << gf.components.bend_s(size=(18, 3), cross_section=xs)
    s_bend2.movey(-0.7)  # Move down by 0.7μm to create parallel waveguide with appropriate gap
    
    # Add ports for connection
    c.add_port("o1", port=s_bend1.ports["o1"])
    c.add_port("o2", port=s_bend1.ports["o2"])
    c.add_port("o3", port=s_bend2.ports["o1"])
    c.add_port("o4", port=s_bend2.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_coupler()
device.write_gds("s_bend_coupler.gds")