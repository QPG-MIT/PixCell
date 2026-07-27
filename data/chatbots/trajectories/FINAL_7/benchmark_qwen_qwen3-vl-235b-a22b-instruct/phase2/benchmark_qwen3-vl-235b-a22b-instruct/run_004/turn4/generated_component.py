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
    coupling_length = 1.0
    
    # Create the racetrack path (bottom part)
    racetrack_path = gf.Path()
    
    # Start from bottom left, go right for coupling section
    racetrack_path.append(gf.path.straight(length=coupling_length))
    
    # Continue with the racetrack
    racetrack_path.append(gf.path.straight(length=straight_length/2))
    
    # Right bend (180 degrees)
    racetrack_path.append(gf.path.euler(radius=bend_radius, angle=180))
    
    # Top straight section
    racetrack_path.append(gf.path.straight(length=straight_length))
    
    # Left bend (180 degrees)
    racetrack_path.append(gf.path.euler(radius=bend_radius, angle=180))
    
    # Bottom straight section to complete the loop
    racetrack_path.append(gf.path.straight(length=straight_length/2))
    
    # Extrude the racetrack path
    racetrack_component = gf.path.extrude(racetrack_path, cross_section=xs)
    racetrack_ref = c << racetrack_component
    
    # Create the top coupling section
    top_coupling_path = gf.Path()
    top_coupling_path.append(gf.path.straight(length=coupling_length))
    
    # Extrude the top coupling path
    top_coupling_component = gf.path.extrude(top_coupling_path, cross_section=xs)
    top_coupling_ref = c << top_coupling_component
    
    # Position the top coupling section above the bottom one
    top_coupling_ref.movey(gap_between_waveguides)
    
    # Add ports for connectivity using the correct method
    # For the bottom waveguide, add port at the beginning
    c.add_port(
        name="o1", 
        center=(racetrack_ref.bbox[0][0], racetrack_ref.bbox[1][1] - 0.25), 
        width=0.5, 
        orientation=180
    )
    
    # For the top coupling waveguide, add port at the beginning
    c.add_port(
        name="o2", 
        center=(top_coupling_ref.bbox[0][0], top_coupling_ref.bbox[1][1] - 0.25), 
        width=0.5, 
        orientation=180
    )
    
    return c

# Create the device
device = racetrack_resonator_with_couplers()
device.write_gds("racetrack_resonator_with_couplers.gds")