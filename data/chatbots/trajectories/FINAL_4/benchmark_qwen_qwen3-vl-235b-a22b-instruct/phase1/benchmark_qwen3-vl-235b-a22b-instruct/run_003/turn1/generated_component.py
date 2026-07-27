import gdsfactory as gf

@gf.cell
def s_bend_pair():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create an S-bend with appropriate size to fit the footprint
    # The footprint is 18x3 um, so I'll make the S-bend size approximately (18, 3)
    # but need to account for the waveguide width in the vertical direction
    s_bend = c << gf.components.bend_s(size=(18, 2.0), cross_section=xs)
    
    # Create a second S-bend below the first one
    # The vertical spacing should be such that the total height is 3um
    # If each waveguide is 0.5um wide, and we want 3um total height,
    # the vertical offset between centers should be 2.5um
    s_bend2 = c << gf.components.bend_s(size=(18, 2.0), cross_section=xs)
    s_bend2.movey(-2.5)  # Move down by 2.5um
    
    # Add ports for the device
    c.add_port("o1_top", port=s_bend.ports["o1"])
    c.add_port("o2_top", port=s_bend.ports["o2"])
    c.add_port("o1_bottom", port=s_bend2.ports["o1"])
    c.add_port("o2_bottom", port=s_bend2.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_pair()
device.write_gds("s_bend_pair.gds")