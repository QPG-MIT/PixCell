import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides - be more explicit
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
    
    # Create left curved section - 5 separate Euler bends for each waveguide
    for i in range(num_waveguides):
        y_offset = i * (waveguide_width + gap) - (num_waveguides - 1) * (waveguide_width + gap) / 2
        # Create a bend that goes from the left end of the waveguide
        left_bend = c << gf.components.bend_euler(radius=30, angle=90, cross_section=xs)
        left_bend.move((0, y_offset))
        left_bend.rotate(90)  # Rotate to make it bend upward
    
    # Create right curved section - 5 separate Euler bends for each waveguide
    for i in range(num_waveguides):
        y_offset = i * (waveguide_width + gap) - (num_waveguides - 1) * (waveguide_width + gap) / 2
        # Create a bend that goes from the right end of the waveguide
        right_bend = c << gf.components.bend_euler(radius=30, angle=90, cross_section=xs)
        right_bend.move((central_length, y_offset))
        right_bend.rotate(-90)  # Rotate to make it bend downward
    
    # Add ports for connectivity
    for i in range(num_waveguides):
        y_offset = i * (waveguide_width + gap) - (num_waveguides - 1) * (waveguide_width + gap) / 2
        
        # Add port at the top end of each left bend
        c.add_port(f"left_{i+1}", 
                   center=(-30, y_offset + 30), 
                   width=0.5, 
                   orientation=180)
        
        # Add port at the bottom end of each right bend
        c.add_port(f"right_{i+1}", 
                   center=(central_length + 30, y_offset - 30), 
                   width=0.5, 
                   orientation=0)
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")