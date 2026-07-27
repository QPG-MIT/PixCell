import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the central region with 5 parallel straight waveguides
    central_length = 120.0  # Total footprint width
    waveguide_width = 0.5
    gap = 0.5
    num_waveguides = 5
    
    # Create each straight waveguide in the central region
    for i in range(num_waveguides):
        y_offset = i * (waveguide_width + gap) - (num_waveguides - 1) * (waveguide_width + gap) / 2
        wg = c << gf.components.straight(length=central_length, cross_section=xs)
        wg.move((0, y_offset))
    
    # Create top curved section
    # Instead of separate S-bends, create a single curved structure that connects to the top waveguides
    # We'll create a large bend that follows the contour of the top waveguides
    top_bend = c << gf.components.bend_euler(radius=30, angle=90, cross_section=xs)
    top_bend.move((central_length/2, (num_waveguides - 1) * (waveguide_width + gap) / 2 + waveguide_width/2))
    top_bend.rotate(90)
    
    # Create bottom curved section
    # Similarly, create a large bend that connects to the bottom waveguides
    bottom_bend = c << gf.components.bend_euler(radius=30, angle=90, cross_section=xs)
    bottom_bend.move((central_length/2, -(num_waveguides - 1) * (waveguide_width + gap) / 2 - waveguide_width/2))
    bottom_bend.rotate(-90)
    
    # Add additional curved sections to complete the device shape
    # These are additional bends to create the full curved structure
    
    # Top additional curves
    for i in range(2):
        top_curve = c << gf.components.bend_euler(radius=30, angle=90, cross_section=xs)
        top_curve.move((central_length/2, (num_waveguides - 1) * (waveguide_width + gap) / 2 + waveguide_width/2 + (i+1)*2))
        top_curve.rotate(90)
    
    # Bottom additional curves
    for i in range(2):
        bottom_curve = c << gf.components.bend_euler(radius=30, angle=90, cross_section=xs)
        bottom_curve.move((central_length/2, -(num_waveguides - 1) * (waveguide_width + gap) / 2 - waveguide_width/2 - (i+1)*2))
        bottom_curve.rotate(-90)
    
    # Add ports for connectivity
    c.add_port("o1", port=top_bend.ports["o1"])
    c.add_port("o2", port=bottom_bend.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")