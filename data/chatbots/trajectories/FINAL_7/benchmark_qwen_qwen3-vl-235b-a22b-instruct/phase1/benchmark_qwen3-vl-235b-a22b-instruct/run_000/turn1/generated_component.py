import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the outer elliptical ring
    outer_radius_x = 2.75  # Half of 5.5 um
    outer_radius_y = 1.5   # Half of 3.0 um (adjusted for better proportion)
    inner_radius_x = 2.25
    inner_radius_y = 1.0
    
    outer_ellipse = gf.components.ellipse(radii=(outer_radius_x, outer_radius_y), layer=(1, 0))
    inner_ellipse = gf.components.ellipse(radii=(inner_radius_x, inner_radius_y), layer=(1, 0))
    
    # Create the ring using boolean operation
    ring = gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=(1, 0))
    ring_ref = c << ring
    
    # Create the two parallel waveguide structures with coupling regions
    coupling_length = 1.0
    gap_between_waveguides = 0.3
    waveguide_width = 0.5
    
    # Create the coupling regions (two parallel waveguides)
    top_coupler = c << gf.components.coupler_straight(length=coupling_length, gap=gap_between_waveguides, cross_section=xs)
    top_coupler.move((0, 0.5))
    
    bottom_coupler = c << gf.components.coupler_straight(length=coupling_length, gap=gap_between_waveguides, cross_section=xs)
    bottom_coupler.move((0, -0.5))
    
    # Create tapered sections to connect to the outer ring
    taper_length = 0.5
    
    # Create paths for the tapered connections
    # Top left connection
    top_left_path = gf.Path()
    top_left_path.append(gf.path.straight(length=0.5))
    top_left_path.append(gf.path.euler(radius=0.5, angle=90, p=0.5))
    top_left_path.append(gf.path.straight(length=0.5))
    
    top_left_taper = gf.path.extrude(top_left_path, cross_section=xs)
    top_left_taper_ref = c << top_left_taper
    top_left_taper_ref.rotate(180)
    top_left_taper_ref.move((-1.5, 0.5))
    
    # Top right connection
    top_right_path = gf.Path()
    top_right_path.append(gf.path.straight(length=0.5))
    top_right_path.append(gf.path.euler(radius=0.5, angle=-90, p=0.5))
    top_right_path.append(gf.path.straight(length=0.5))
    
    top_right_taper = gf.path.extrude(top_right_path, cross_section=xs)
    top_right_taper_ref = c << top_right_taper
    top_right_taper_ref.move((1.5, 0.5))
    
    # Bottom left connection
    bottom_left_path = gf.Path()
    bottom_left_path.append(gf.path.straight(length=0.5))
    bottom_left_path.append(gf.path.euler(radius=0.5, angle=-90, p=0.5))
    bottom_left_path.append(gf.path.straight(length=0.5))
    
    bottom_left_taper = gf.path.extrude(bottom_left_path, cross_section=xs)
    bottom_left_taper_ref = c << bottom_left_taper
    bottom_left_taper_ref.rotate(180)
    bottom_left_taper_ref.move((-1.5, -0.5))
    
    # Bottom right connection
    bottom_right_path = gf.Path()
    bottom_right_path.append(gf.path.straight(length=0.5))
    bottom_right_path.append(gf.path.euler(radius=0.5, angle=90, p=0.5))
    bottom_right_path.append(gf.path.straight(length=0.5))
    
    bottom_right_taper = gf.path.extrude(bottom_right_path, cross_section=xs)
    bottom_right_taper_ref = c << bottom_right_taper
    bottom_right_taper_ref.move((1.5, -0.5))
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")