import gdsfactory as gf

@gf.cell
def create_racetrack_resonator_with_coupler():
    c = gf.Component()

    # Define a custom cross-section with small min_bend_radius
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=2.0  # minimum bend radius for this cross-section
    )

    # Device dimensions based on footprint constraint
    total_width = 3.0
    total_height = 5.5

    # Racetrack parameters
    straight_length = 2.0
    bend_radius = (total_height - straight_length) / 2  # ~1.75 µm

    # Ensure bend_radius is at least the cross-section's minimum
    if bend_radius < xs.radius:
        bend_radius = xs.radius

    # Create the racetrack path (open loop with coupling waveguide)
    p = gf.Path()
    p.append(gf.path.euler(radius=bend_radius, angle=180))  # Left Euler bend (top half)
    p.append(gf.path.straight(length=straight_length))      # Top straight
    p.append(gf.path.euler(radius=bend_radius, angle=180))  # Right Euler bend (bottom half)
    p.append(gf.path.straight(length=straight_length))      # Bottom straight
    
    # Extrude the racetrack path
    racetrack = gf.path.extrude(p, cross_section=xs)
    racetrack_ref = c << racetrack

    # Create coupling waveguide (single waveguide on the right side)
    coupling_length = 1.5
    coupling_gap = 0.2
    
    # Create coupling waveguide path
    coupling_path = gf.Path()
    coupling_path.append(gf.path.straight(length=coupling_length))
    
    # Extrude coupling waveguide
    coupling = gf.path.extrude(coupling_path, cross_section=xs)
    coupling_ref = c << coupling
    
    # Position coupling waveguide outside racetrack, parallel to right straight section
    # Calculate position to place coupling waveguide to the right of the racetrack
    coupling_x = straight_length + bend_radius + coupling_gap
    coupling_y = 0  # Centered vertically
    
    coupling_ref.move((coupling_x, coupling_y))

    # Add ports for connection
    c.add_port("racetrack_in", port=racetrack_ref.ports["o1"])
    c.add_port("racetrack_out", port=racetrack_ref.ports["o2"])
    c.add_port("coupler_in", port=coupling_ref.ports["o1"])
    c.add_port("coupler_out", port=coupling_ref.ports["o2"])

    return c

# Create the device
device = create_racetrack_resonator_with_coupler()
device.write_gds("racetrack_resonator_with_coupler.gds")