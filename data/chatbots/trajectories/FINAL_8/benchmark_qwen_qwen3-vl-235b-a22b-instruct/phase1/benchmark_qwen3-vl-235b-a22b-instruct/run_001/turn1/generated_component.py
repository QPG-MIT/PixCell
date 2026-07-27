import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the central region with 5 parallel straight waveguides
    # Each waveguide is 0.5μm wide with 0.5μm gap between them
    central_length = 120.0  # Total footprint width
    waveguide_width = 0.5
    gap = 0.5
    num_waveguides = 5
    
    # Calculate total height needed for central region
    central_height = (num_waveguides - 1) * (waveguide_width + gap) + waveguide_width
    
    # Create each straight waveguide in the central region
    for i in range(num_waveguides):
        y_offset = i * (waveguide_width + gap) - central_height / 2 + waveguide_width / 2
        wg = c << gf.components.straight(length=central_length, cross_section=xs)
        wg.move((0, y_offset))
    
    # Create top S-bend section
    # The S-bend connects the top waveguide to the top curved section
    top_s_bend = c << gf.components.bend_s(size=(60, 2), cross_section=xs)
    top_s_bend.move((central_length/2, central_height/2 + waveguide_width/2 + 1))
    top_s_bend.rotate(180)
    
    # Create bottom S-bend section
    # The S-bend connects the bottom waveguide to the bottom curved section
    bottom_s_bend = c << gf.components.bend_s(size=(60, 2), cross_section=xs)
    bottom_s_bend.move((central_length/2, -central_height/2 - waveguide_width/2 - 1))
    
    # Add additional curved sections to complete the device shape
    # These are additional S-bends to create the full curved structure
    
    # Top additional curves
    for i in range(2):
        top_curve = c << gf.components.bend_s(size=(60, 2), cross_section=xs)
        top_curve.move((central_length/2, central_height/2 + waveguide_width/2 + 1 + (i+1)*2))
        top_curve.rotate(180)
    
    # Bottom additional curves
    for i in range(2):
        bottom_curve = c << gf.components.bend_s(size=(60, 2), cross_section=xs)
        bottom_curve.move((central_length/2, -central_height/2 - waveguide_width/2 - 1 - (i+1)*2))
    
    # Add ports for connectivity
    c.add_port("o1", port=top_s_bend.ports["o1"])
    c.add_port("o2", port=bottom_s_bend.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")