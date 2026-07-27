import gdsfactory as gf

@gf.cell
def create_racetrack_resonator():
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=2.0  # minimum bend radius
    )
    
    # Device dimensions based on footprint constraint
    total_width = 3.0
    total_height = 5.5
    
    # Racetrack parameters for open structure
    # For an open racetrack, we need one straight section and two bends
    straight_length = 2.0  # Length of the straight section
    bend_radius = (total_height - straight_length) / 2  # ~1.75 µm
    
    # Ensure bend_radius is at least the cross-section's minimum
    if bend_radius < xs.radius:
        bend_radius = xs.radius
    
    # Create the open racetrack path (not a closed loop)
    p = gf.Path()
    p.append(gf.path.euler(radius=bend_radius, angle=180))  # First Euler bend (180° turn)
    p.append(gf.path.straight(length=straight_length))      # Straight section
    p.append(gf.path.euler(radius=bend_radius, angle=180))  # Second Euler bend (180° turn)
    
    # Extrude the racetrack path
    racetrack = gf.path.extrude(p, cross_section=xs)
    racetrack_ref = c << racetrack
    
    # Add ports for connection (at the two ends of the path)
    c.add_port("in", port=racetrack_ref.ports["o1"])
    c.add_port("out", port=racetrack_ref.ports["o2"])
    
    return c

# Create the device
device = create_racetrack_resonator()
device.write_gds("racetrack_resonator.gds")