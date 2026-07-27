import gdsfactory as gf

@gf.cell
def s_bend_device():
    c = gf.Component()
    
    # Create a cross-section for the waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create S-bend with size matching the footprint constraint
    # Size is (dx, dy) - the horizontal and vertical offsets
    # We use (18, 3) to match the footprint constraint
    s_bend = c << gf.components.bend_s(size=(18, 3), cross_section=xs)
    
    # Expose the input and output ports
    c.add_port("o1", port=s_bend.ports["o1"])
    c.add_port("o2", port=s_bend.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_device()
device.write_gds("s_bend_device.gds")