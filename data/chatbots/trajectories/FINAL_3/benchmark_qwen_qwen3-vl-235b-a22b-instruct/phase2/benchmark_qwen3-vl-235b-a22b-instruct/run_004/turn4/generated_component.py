import gdsfactory as gf

@gf.cell
def directional_coupler():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Parameters based on footprint (120um x 4um)
    total_length = 120.0
    waveguide_width = 0.5
    gap = 0.5  # gap between waveguides in parallel section
    taper_length = 20.0  # length of taper sections
    
    # Calculate straight section length
    straight_length = total_length - 2 * taper_length
    
    # Create the directional coupler structure
    # We need two waveguides that start apart, come together, run parallel, then separate
    
    # Create the top waveguide
    top_waveguide = c << gf.components.straight(length=straight_length, cross_section=xs)
    top_waveguide.move((taper_length, gap/2 + waveguide_width/2))
    
    # Create the bottom waveguide
    bottom_waveguide = c << gf.components.straight(length=straight_length, cross_section=xs)
    bottom_waveguide.move((taper_length, -gap/2 - waveguide_width/2))
    
    # Create input taper sections (bringing waveguides together)
    # Top input taper
    top_input_taper = c << gf.components.taper(length=taper_length, width1=waveguide_width, width2=waveguide_width)
    top_input_taper.move((0, gap/2 + waveguide_width/2))
    top_input_taper.rotate(180)  # Point towards the straight section
    
    # Bottom input taper
    bottom_input_taper = c << gf.components.taper(length=taper_length, width1=waveguide_width, width2=waveguide_width)
    bottom_input_taper.move((0, -gap/2 - waveguide_width/2))
    bottom_input_taper.rotate(180)  # Point towards the straight section
    
    # Create output taper sections (separating waveguides)
    # Top output taper
    top_output_taper = c << gf.components.taper(length=taper_length, width1=waveguide_width, width2=waveguide_width)
    top_output_taper.move((taper_length + straight_length, gap/2 + waveguide_width/2))
    
    # Bottom output taper
    bottom_output_taper = c << gf.components.taper(length=taper_length, width1=waveguide_width, width2=waveguide_width)
    bottom_output_taper.move((taper_length + straight_length, -gap/2 - waveguide_width/2))
    
    # Connect the components
    # Connect input tapers to straight sections
    top_input_taper.connect("o2", top_waveguide.ports["o1"])
    bottom_input_taper.connect("o2", bottom_waveguide.ports["o1"])
    
    # Connect straight sections to output tapers
    top_waveguide.connect("o2", top_output_taper.ports["o1"])
    bottom_waveguide.connect("o2", bottom_output_taper.ports["o1"])
    
    # Add ports
    c.add_port("o1_top", port=top_input_taper.ports["o1"])
    c.add_port("o1_bottom", port=bottom_input_taper.ports["o1"])
    c.add_port("o2_top", port=top_output_taper.ports["o2"])
    c.add_port("o2_bottom", port=bottom_output_taper.ports["o2"])
    
    return c

# Create and save the device
device = directional_coupler()
device.write_gds("directional_coupler.gds")