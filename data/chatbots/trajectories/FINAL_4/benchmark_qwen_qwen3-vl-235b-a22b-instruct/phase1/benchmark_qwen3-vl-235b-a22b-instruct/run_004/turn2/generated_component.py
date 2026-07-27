import gdsfactory as gf

@gf.cell
def s_bend_coupler():
    c = gf.Component()
    
    # Define cross-section for waveguides with explicit layer
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create top S-bend waveguide
    top_s_bend = gf.components.bend_s(size=(18, 3), cross_section=xs)
    top_ref = c << top_s_bend
    top_ref.move((0, 0.25))
    
    # Create bottom S-bend waveguide
    bottom_s_bend = gf.components.bend_s(size=(18, 3), cross_section=xs)
    bottom_ref = c << bottom_s_bend
    bottom_ref.move((0, -0.25))
    
    # Add ports for connectivity
    # Get the ports from the original components and add them to the main component
    top_ports = top_s_bend.get_ports_list()
    bottom_ports = bottom_s_bend.get_ports_list()
    
    # Add ports to the main component with proper positioning
    if len(top_ports) >= 2:
        c.add_port("o1", port=top_ports[0].move((0, 0.25)))
        c.add_port("o2", port=top_ports[1].move((0, 0.25)))
    if len(bottom_ports) >= 2:
        c.add_port("o3", port=bottom_ports[0].move((0, -0.25)))
        c.add_port("o4", port=bottom_ports[1].move((0, -0.25)))
    
    return c

# Create and save the device
device = s_bend_coupler()
device.write_gds("s_bend_coupler.gds")