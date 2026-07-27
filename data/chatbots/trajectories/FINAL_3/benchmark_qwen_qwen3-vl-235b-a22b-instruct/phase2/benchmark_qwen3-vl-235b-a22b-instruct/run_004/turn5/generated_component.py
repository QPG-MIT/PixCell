import gdsfactory as gf

@gf.cell
def parallel_waveguides():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Parameters based on footprint (120um x 4um)
    total_length = 120.0
    waveguide_width = 0.5
    gap = 1.0  # gap between waveguides (adjusted to fit within 4um height)
    
    # Calculate vertical positions to fit within 4um height
    # Total height needed: 2 * waveguide_width + gap = 1.0 + 1.0 = 2.0um
    # So we have plenty of room within the 4um constraint
    
    # Create the top waveguide
    top_waveguide = c << gf.components.straight(length=total_length, cross_section=xs)
    top_waveguide.move((0, gap/2 + waveguide_width/2))
    
    # Create the bottom waveguide
    bottom_waveguide = c << gf.components.straight(length=total_length, cross_section=xs)
    bottom_waveguide.move((0, -gap/2 - waveguide_width/2))
    
    # Add ports
    c.add_port("o1_top", port=top_waveguide.ports["o1"])
    c.add_port("o1_bottom", port=bottom_waveguide.ports["o1"])
    c.add_port("o2_top", port=top_waveguide.ports["o2"])
    c.add_port("o2_bottom", port=bottom_waveguide.ports["o2"])
    
    return c

# Create and save the device
device = parallel_waveguides()
device.write_gds("parallel_waveguides.gds")