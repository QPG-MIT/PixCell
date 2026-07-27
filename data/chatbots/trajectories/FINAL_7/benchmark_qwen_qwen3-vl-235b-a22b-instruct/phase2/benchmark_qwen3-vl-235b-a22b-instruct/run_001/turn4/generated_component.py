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
    
    # Racetrack parameters
    # For a racetrack, we need two straight sections and two semicircular bends
    # The total height constrains our bend radius
    straight_length = 2.0  # This will be the length of the straight sections
    bend_radius = (total_height - straight_length) / 2  # ~1.75 µm
    
    # Ensure bend_radius is at least the cross-section's minimum
    if bend_radius < xs.radius:
        bend_radius = xs.radius
    
    # Create the racetrack path (closed loop)
    p = gf.Path()
    p.append(gf.path.euler(radius=bend_radius, angle=180))  # Left Euler bend (top half)
    p.append(gf.path.straight(length=straight_length))      # Top straight
    p.append(gf.path.euler(radius=bend_radius, angle=180))  # Right Euler bend (bottom half)
    p.append(gf.path.straight(length=straight_length))      # Bottom straight
    
    # Extrude the racetrack path
    racetrack = gf.path.extrude(p, cross_section=xs)
    racetrack_ref = c << racetrack
    
    # Add ports for connection (at the ends of the bottom straight section)
    c.add_port("in", port=racetrack_ref.ports["o1"])
    c.add_port("out", port=racetrack_ref.ports["o2"])
    
    return c

# Create the device
device = create_racetrack_resonator()
device.write_gds("racetrack_resonator.gds")