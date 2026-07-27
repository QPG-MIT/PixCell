import gdsfactory as gf

@gf.cell
def straight_vertical_waveguide():
    c = gf.Component()
    
    # Create a cross-section for the waveguide
    xs = gf.cross_section.cross_section(width=3.0, layer=(1, 0))  # Width matches footprint constraint
    
    # Create a straight path oriented vertically (along Y-axis)
    p = gf.path.straight(length=18.0)  # Length matches footprint constraint
    
    # Extrude the path to create the waveguide
    wg = c << gf.path.extrude(p, cross_section=xs)
    
    # Rotate the waveguide 90 degrees to make it vertical
    wg.rotate(90)
    
    # Expose the input and output ports
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    
    return c

# Create and save the device
device = straight_vertical_waveguide()
device.write_gds("straight_vertical_waveguide.gds")