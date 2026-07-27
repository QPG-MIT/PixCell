import gdsfactory as gf

@gf.cell
def y_junction():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create two straight waveguides on the left
    wg1 = c << gf.components.straight(length=10, cross_section=xs)
    wg2 = c << gf.components.straight(length=10, cross_section=xs)
    
    # Position wg2 below wg1 with 0.7μm center-to-center spacing (0.2μm gap if width=0.5μm)
    wg2.movey(-0.7)
    
    # Create smooth, gradual separation using S-bends (which are parametric and supported)
    # Upper S-bend: dx=20μm (horizontal), dy=3μm (vertical offset)
    s_bend_upper = c << gf.components.bend_s(size=(20, 3), cross_section=xs)
    s_bend_upper.connect("o1", wg1.ports["o2"])
    
    # Lower S-bend: mirror to go downward
    s_bend_lower = c << gf.components.bend_s(size=(20, 3), cross_section=xs)
    s_bend_lower.connect("o1", wg2.ports["o2"])
    s_bend_lower.mirror()
    
    # Add ports for external connections
    c.add_port("o1", port=s_bend_upper.ports["o2"])
    c.add_port("o2", port=s_bend_lower.ports["o2"])
    c.add_port("o3", port=wg1.ports["o1"])
    c.add_port("o4", port=wg2.ports["o1"])
    
    return c

# Create the device
device = y_junction()

# Write to GDS file
device.write_gds("y_junction.gds")