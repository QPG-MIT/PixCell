import gdsfactory as gf

@gf.cell
def create_racetrack_resonator_with_couplers():
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

    # Create the racetrack path (closed loop)
    p = gf.Path()
    p.append(gf.path.arc(radius=bend_radius, angle=180))  # Left semicircle (top half)
    p.append(gf.path.straight(length=straight_length))    # Top straight
    p.append(gf.path.arc(radius=bend_radius, angle=180))  # Right semicircle (bottom half)
    p.append(gf.path.straight(length=straight_length))    # Bottom straight

    # Extrude the racetrack path
    racetrack = gf.path.extrude(p, cross_section=xs)
    racetrack_ref = c << racetrack

    # Create coupling waveguides
    coupling_length = 1.5
    coupling_gap = 0.2

    # Create top coupling waveguide
    coupling_top_path = gf.Path()
    coupling_top_path.append(gf.path.straight(length=coupling_length))
    coupling_top = gf.path.extrude(coupling_top_path, cross_section=xs)
    coupling_top_ref = c << coupling_top
    # Position top coupling waveguide inside racetrack, above center
    coupling_top_ref.move((straight_length/2 - coupling_length/2, coupling_gap/2))

    # Create bottom coupling waveguide
    coupling_bottom_path = gf.Path()
    coupling_bottom_path.append(gf.path.straight(length=coupling_length))
    coupling_bottom = gf.path.extrude(coupling_bottom_path, cross_section=xs)
    coupling_bottom_ref = c << coupling_bottom
    # Position bottom coupling waveguide inside racetrack, below center
    coupling_bottom_ref.move((straight_length/2 - coupling_length/2, -coupling_gap/2))

    return c

# Create the device
device = create_racetrack_resonator_with_couplers()
device.write_gds("racetrack_resonator_with_couplers.gds")