import gdsfactory as gf

@gf.cell
def y_junction():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create single straight waveguide on the left (input)
    wg = c << gf.components.straight(length=10, cross_section=xs)
    
    # Create upper S-bend for the top output
    s_bend_upper = c << gf.components.bend_s(size=(20, 3), cross_section=xs)
    s_bend_upper.connect("o1", wg.ports["o2"])
    
    # Create lower S-bend for the bottom output (mirror to go downward)
    s_bend_lower = c << gf.components.bend_s(size=(20, 3), cross_section=xs)
    s_bend_lower.connect("o1", wg.ports["o2"])
    s_bend_lower.mirror()
    
    # Add ports for external connections
    c.add_port("o1", port=wg.ports["o1"])  # Input port
    c.add_port("o2", port=s_bend_upper.ports["o2"])  # Upper output
    c.add_port("o3", port=s_bend_lower.ports["o2"])  # Lower output
    
    return c

# Create the device
device = y_junction()

# Write to GDS file
device.write_gds("y_junction.gds")