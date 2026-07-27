import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define layer
    layer = (1, 0)
    
    # Create the outer elliptical ring
    outer_radius_x = 2.75  # Half of 5.5 um
    outer_radius_y = 1.5   # Half of 3.0 um
    inner_radius_x = 2.25
    inner_radius_y = 1.0
    
    outer_ellipse = gf.components.ellipse(radii=(outer_radius_x, outer_radius_y), layer=layer)
    inner_ellipse = gf.components.ellipse(radii=(inner_radius_x, inner_radius_y), layer=layer)
    
    # Create the ring using boolean operation
    ring = gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=layer)
    ring_ref = c << ring
    
    # Create the two parallel waveguide structures with coupling regions
    waveguide_width = 0.5
    coupling_length = 1.0
    gap_between_waveguides = 0.3
    taper_length = 1.0
    
    # Create the central coupling region (two parallel rectangles with gaps)
    # Top coupling region
    top_coupling = gf.components.rectangle(size=(coupling_length, waveguide_width), layer=layer)
    top_coupling_ref = c << top_coupling
    top_coupling_ref.move((0, 0.5))
    
    # Bottom coupling region
    bottom_coupling = gf.components.rectangle(size=(coupling_length, waveguide_width), layer=layer)
    bottom_coupling_ref = c << bottom_coupling
    bottom_coupling_ref.move((0, -0.5))
    
    # Create the tapered sections connecting to the outer ring
    # Top left taper
    top_left_taper = gf.components.taper(length=taper_length, width1=waveguide_width, width2=0.3)
    top_left_taper_ref = c << top_left_taper
    top_left_taper_ref.rotate(180)
    top_left_taper_ref.move((-1.5, 0.5))
    
    # Top right taper
    top_right_taper = gf.components.taper(length=taper_length, width1=waveguide_width, width2=0.3)
    top_right_taper_ref = c << top_right_taper
    top_right_taper_ref.move((1.5, 0.5))
    
    # Bottom left taper
    bottom_left_taper = gf.components.taper(length=taper_length, width1=waveguide_width, width2=0.3)
    bottom_left_taper_ref = c << bottom_left_taper
    bottom_left_taper_ref.rotate(180)
    bottom_left_taper_ref.move((-1.5, -0.5))
    
    # Bottom right taper
    bottom_right_taper = gf.components.taper(length=taper_length, width1=waveguide_width, width2=0.3)
    bottom_right_taper_ref = c << bottom_right_taper
    bottom_right_taper_ref.move((1.5, -0.5))
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")