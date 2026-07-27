import gdsfactory as gf

@gf.cell
def straight_waveguide_pair():
    c = gf.Component()
    
    # Define cross-section for waveguides with explicit parameters
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        # Ensure we're using a simple rectangular cross-section
        sections=None
    )
    
    # Create first straight waveguide
    wg1 = c << gf.components.straight(length=18, cross_section=xs)
    
    # Create second straight waveguide below the first one
    # Position it exactly 1.0um below to maintain the 3um total height constraint
    # (0.5um waveguide + 1.0um gap + 0.5um waveguide = 2.0um total, which fits in 3um)
    wg2 = c << gf.components.straight(length=18, cross_section=xs)
    wg2.movey(-1.0)  # Move down by 1.0um
    
    # Add ports for the device
    c.add_port("o1_top", port=wg1.ports["o1"])
    c.add_port("o2_top", port=wg1.ports["o2"])
    c.add_port("o1_bottom", port=wg2.ports["o1"])
    c.add_port("o2_bottom", port=wg2.ports["o2"])
    
    return c

# Create and save the device
device = straight_waveguide_pair()
device.write_gds("straight_waveguide_pair.gds")