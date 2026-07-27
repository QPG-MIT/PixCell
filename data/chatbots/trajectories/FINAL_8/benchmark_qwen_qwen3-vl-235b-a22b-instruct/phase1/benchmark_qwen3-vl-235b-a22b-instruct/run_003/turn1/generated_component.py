import gdsfactory as gf

@gf.cell
def directional_coupler_symmetric():
    c = gf.Component()
    
    # Define cross-section for waveguides
    # Create a proper cross-section with layer specification
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        sections=[gf.Section(width=0.5, layer=(1, 0))]
    )
    
    # Parameters
    central_length = 40.0  # Length of central coupling region
    bend_radius = 20.0    # Radius of bends
    gap = 0.2           # Gap between waveguides
    waveguide_width = 0.5 # Width of each waveguide
    
    # Create 4 parallel straight waveguides in the center
    for i in range(4):
        y_offset = (i - 1.5) * (waveguide_width + gap)
        straight = c << gf.components.straight(length=central_length, cross_section=xs)
        straight.move((0, y_offset))
    
    # Create top curved section (4 waveguides curving down)
    for i in range(4):
        y_offset = (i - 1.5) * (waveguide_width + gap)
        # Create a bend that curves down
        bend = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
        bend.rotate(90)  # Rotate to point downward
        bend.move((central_length/2, y_offset + bend_radius))
    
    # Create bottom curved section (4 waveguides curving up)
    for i in range(4):
        y_offset = (i - 1.5) * (waveguide_width + gap)
        # Create a bend that curves up
        bend = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
        bend.rotate(-90)  # Rotate to point upward
        bend.move((central_length/2, y_offset - bend_radius))
    
    # Add ports for the top and bottom sections
    for i in range(4):
        y_offset = (i - 1.5) * (waveguide_width + gap)
        # Top ports
        c.add_port(f"top_{i+1}", center=(central_length/2 + bend_radius, y_offset + bend_radius), width=waveguide_width, orientation=90)
        # Bottom ports
        c.add_port(f"bottom_{i+1}", center=(central_length/2 + bend_radius, y_offset - bend_radius), width=waveguide_width, orientation=-90)
    
    return c

# Create the device
device = directional_coupler_symmetric()
device.write_gds("directional_coupler_symmetric.gds")