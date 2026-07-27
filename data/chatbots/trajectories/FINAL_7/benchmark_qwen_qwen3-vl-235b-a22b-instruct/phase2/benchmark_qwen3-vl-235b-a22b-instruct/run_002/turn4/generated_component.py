import gdsfactory as gf

@gf.cell
def racetrack_resonator_with_couplers():
    c = gf.Component()
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the racetrack resonator (open, not closed)
    straight_length = 2.0
    bend_radius = 0.75
    
    # Create the path for the open racetrack
    # Start with a straight section
    path = gf.path.straight(length=straight_length)
    # Add a 180° bend (half circle)
    path += gf.path.euler(radius=bend_radius, angle=180)
    # Add another straight section
    path += gf.path.straight(length=straight_length)
    # Add another 180° bend (half circle)
    path += gf.path.euler(radius=bend_radius, angle=180)
    # Add a final straight section to complete the open racetrack
    path += gf.path.straight(length=straight_length)
    
    # Extrude the path to create the racetrack
    racetrack = gf.path.extrude(path, cross_section=xs)
    
    # Create the straight bus waveguide
    bus_length = straight_length + 2.0  # Slightly longer than racetrack straight section
    bus_waveguide = gf.components.straight(length=bus_length, cross_section=xs)
    
    # Add both components to the main component
    racetrack_ref = c << racetrack
    bus_ref = c << bus_waveguide
    
    # Position the bus waveguide parallel to the racetrack
    # The gap between racetrack and bus should be small for coupling
    coupling_gap = 0.2
    
    # Calculate the vertical position for the bus waveguide
    # Position the bus waveguide to couple with the middle straight section of the racetrack
    bus_y_position = -(bend_radius + coupling_gap + xs.width/2)
    
    # Position the bus waveguide
    bus_ref.movey(bus_y_position)
    
    # Center the bus horizontally with the middle straight section of the racetrack
    # The middle straight section is the second straight section in our path
    # It starts after the first straight and first bend
    # The first straight is length=straight_length
    # The first bend has a radius of bend_radius, so the center of the bend is at x=straight_length + bend_radius
    # The middle straight section starts at x=straight_length + 2*bend_radius
    bus_ref.movex(straight_length + 2*bend_radius - bus_length/2)
    
    # Add ports for the bus waveguide
    c.add_port("bus_in", port=bus_ref.ports["o1"])
    c.add_port("bus_out", port=bus_ref.ports["o2"])
    
    # Add ports for the racetrack (at the ends for coupling)
    c.add_port("resonator_in", port=racetrack.ports["o1"])
    c.add_port("resonator_out", port=racetrack.ports["o2"])
    
    return c

# Create the device
device = racetrack_resonator_with_couplers()
device.write_gds("racetrack_resonator_with_couplers.gds")