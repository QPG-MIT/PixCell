import gdsfactory as gf

@gf.cell
def racetrack_resonator_with_couplers():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=5.0,
        radius_min=1.0
    )
    
    # Parameters for the racetrack
    straight_length = 2.0
    bend_radius = 0.75
    gap_between_waveguides = 0.5
    
    # Create the racetrack path with coupling region
    racetrack_path = gf.Path()
    
    # Start from bottom left, go right
    racetrack_path.append(gf.path.straight(length=straight_length/2 - 0.5))
    
    # Add coupling region - this will be two parallel straight sections
    # First section (bottom)
    racetrack_path.append(gf.path.straight(length=1.0))
    
    # Create a second path for the top section of the coupling
    top_coupling_path = gf.Path()
    top_coupling_path.append(gf.path.straight(length=straight_length/2 - 0.5))
    top_coupling_path.append(gf.path.straight(length=1.0))
    top_coupling_path.movey(gap_between_waveguides)
    
    # Continue with bottom path
    racetrack_path.append(gf.path.straight(length=straight_length/2 - 0.5))
    
    # Right bend (180 degrees)
    racetrack_path.append(gf.path.euler(radius=bend_radius, angle=180))
    
    # Top straight section
    racetrack_path.append(gf.path.straight(length=straight_length/2 - 0.5))
    racetrack_path.append(gf.path.straight(length=1.0))
    racetrack_path.append(gf.path.straight(length=straight_length/2 - 0.5))
    
    # Left bend (180 degrees)
    racetrack_path.append(gf.path.euler(radius=bend_radius, angle=180))
    
    # Extrude the racetrack path
    racetrack = c << gf.path.extrude(racetrack_path, cross_section=xs)
    
    # Extrude the top coupling path
    top_coupling = c << gf.path.extrude(top_coupling_path, cross_section=xs)
    
    # Add ports for connectivity
    c.add_port("o1", port=racetrack.ports["o1"])
    c.add_port("o2", port=racetrack.ports["o2"])
    
    return c

# Create the device
device = racetrack_resonator_with_couplers()
device.write_gds("racetrack_resonator_with_couplers.gds")