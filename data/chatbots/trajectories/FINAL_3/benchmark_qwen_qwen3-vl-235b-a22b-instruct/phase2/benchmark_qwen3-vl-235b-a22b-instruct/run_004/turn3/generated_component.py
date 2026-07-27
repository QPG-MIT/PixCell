import gdsfactory as gf

@gf.cell
def tapered_coupler():
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
    
    # Create the tapered coupler structure
    # Start with a single waveguide
    input_taper = c << gf.components.taper(length=taper_length, width1=waveguide_width, width2=waveguide_width)
    input_taper.move((0, 0))
    
    # Create the splitting section - this is the key change
    # We need to create a structure that splits the single waveguide into two
    # Create two parallel waveguides with appropriate spacing
    
    # Create the top waveguide path
    top_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    top_straight.move((taper_length, gap/2 + waveguide_width/2))
    
    # Create the bottom waveguide path  
    bottom_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    bottom_straight.move((taper_length, -gap/2 - waveguide_width/2))
    
    # Create the output taper section (rejoining)
    output_taper = c << gf.components.taper(length=taper_length, width1=waveguide_width, width2=waveguide_width)
    output_taper.move((taper_length + straight_length, 0))
    
    # Add smooth bends to connect the sections
    # Create bend to transition from input to top waveguide
    top_bend = c << gf.components.bend_euler(radius=10, angle=90, cross_section=xs)
    top_bend.rotate(180)  # Rotate to point upward
    top_bend.move((taper_length, 0))
    top_bend.connect("o1", input_taper.ports["o2"])
    
    # Create bend to transition from input to bottom waveguide
    bottom_bend = c << gf.components.bend_euler(radius=10, angle=-90, cross_section=xs)
    bottom_bend.rotate(180)  # Rotate to point downward
    bottom_bend.move((taper_length, 0))
    bottom_bend.connect("o1", input_taper.ports["o2"])
    
    # Connect the top waveguide to the output
    top_output_bend = c << gf.components.bend_euler(radius=10, angle=-90, cross_section=xs)
    top_output_bend.move((taper_length + straight_length, gap/2 + waveguide_width/2))
    top_output_bend.connect("o1", top_straight.ports["o2"])
    top_output_bend.connect("o2", output_taper.ports["o1"])
    
    # Connect the bottom waveguide to the output
    bottom_output_bend = c << gf.components.bend_euler(radius=10, angle=90, cross_section=xs)
    bottom_output_bend.move((taper_length + straight_length, -gap/2 - waveguide_width/2))
    bottom_output_bend.connect("o1", bottom_straight.ports["o2"])
    bottom_output_bend.connect("o2", output_taper.ports["o1"])
    
    # Add ports
    c.add_port("o1", port=input_taper.ports["o1"])
    c.add_port("o2", port=output_taper.ports["o2"])
    
    return c

# Create and save the device
device = tapered_coupler()
device.write_gds("tapered_coupler.gds")