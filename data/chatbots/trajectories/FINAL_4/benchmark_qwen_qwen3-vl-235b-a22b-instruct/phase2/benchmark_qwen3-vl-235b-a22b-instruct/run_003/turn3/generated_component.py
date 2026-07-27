import gdsfactory as gf

@gf.cell
def straight_waveguide_pair():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create first straight waveguide
    wg1 = c << gf.components.straight(length=18, cross_section=xs)
    
    # Create second straight waveguide below the first one
    # To fit within 3um height constraint with 0.5um waveguide width,
    # we need to position them with appropriate spacing
    wg2 = c << gf.components.straight(length=18, cross_section=xs)
    wg2.movey(-1.0)  # Move down by 1.0um to create the desired spacing
    
    # Add ports for the device
    c.add_port("o1_top", port=wg1.ports["o1"])
    c.add_port("o2_top", port=wg1.ports["o2"])
    c.add_port("o1_bottom", port=wg2.ports["o1"])
    c.add_port("o2_bottom", port=wg2.ports["o2"])
    
    return c

# Create and save the device
device = straight_waveguide_pair()
device.write_gds("straight_waveguide_pair.gds")