import gdsfactory as gf

@gf.cell
def s_bend_pair_corrected():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create an S-bend with a much smaller vertical size to fit the 3um height constraint
    # The original image shows very tight spacing between the two waveguides
    # Let's use a smaller vertical size for the S-bend
    s_bend = c << gf.components.bend_s(size=(18, 1.0), cross_section=xs)
    
    # Create a second S-bend below the first one
    # The vertical spacing should be such that the total height is 3um
    # With 0.5um waveguide width and very small gap between them, 
    # the vertical offset between centers should be approximately 1.0um
    s_bend2 = c << gf.components.bend_s(size=(18, 1.0), cross_section=xs)
    s_bend2.movey(-1.0)  # Move down by 1.0um to create the tight spacing
    
    # Add ports for the device
    c.add_port("o1_top", port=s_bend.ports["o1"])
    c.add_port("o2_top", port=s_bend.ports["o2"])
    c.add_port("o1_bottom", port=s_bend2.ports["o1"])
    c.add_port("o2_bottom", port=s_bend2.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_pair_corrected()
device.write_gds("s_bend_pair_corrected.gds")