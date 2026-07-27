import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define layer
    layer = (1, 0)
    
    # Create the racetrack resonator shape (asymmetric ellipse with straight sections)
    # This will be created using paths for smooth curves
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Create the main racetrack path
    path = gf.Path()
    path.append(gf.path.arc(radius=1.0, angle=180))  # Left semicircle
    path.append(gf.path.straight(length=3.5))        # Top straight section
    path.append(gf.path.arc(radius=1.0, angle=180))  # Right semicircle
    path.append(gf.path.straight(length=3.5))        # Bottom straight section
    
    # Create the racetrack resonator
    racetrack = gf.path.extrude(path, cross_section=xs)
    racetrack_ref = c << racetrack
    racetrack_ref.move((-1.75, 0))  # Center the racetrack
    
    # Create the coupling waveguides
    # Top coupling waveguide
    top_waveguide_path = gf.Path()
    top_waveguide_path.append(gf.path.straight(length=2.0))
    top_waveguide = gf.path.extrude(top_waveguide_path, cross_section=xs)
    top_waveguide_ref = c << top_waveguide
    top_waveguide_ref.move((0, 0.7))  # Position above the racetrack
    
    # Bottom coupling waveguide  
    bottom_waveguide_path = gf.Path()
    bottom_waveguide_path.append(gf.path.straight(length=2.0))
    bottom_waveguide = gf.path.extrude(bottom_waveguide_path, cross_section=xs)
    bottom_waveguide_ref = c << bottom_waveguide
    bottom_waveguide_ref.move((0, -0.7))  # Position below the racetrack
    
    # Create the coupling region (make it wider for better coupling)
    coupling_length = 1.0
    coupling_gap = 0.3
    
    # Create coupling region using rectangle for simplicity
    coupling_region = gf.components.rectangle(
        size=(coupling_length, 0.5), 
        layer=layer
    )
    coupling_region_ref = c << coupling_region
    coupling_region_ref.move((0, 0.5))
    
    # Create second coupling region
    coupling_region2 = gf.components.rectangle(
        size=(coupling_length, 0.5), 
        layer=layer
    )
    coupling_region2_ref = c << coupling_region2
    coupling_region2_ref.move((0, -0.5))
    
    # Create tapered sections for smooth transition
    taper_length = 0.5
    
    # Left taper for top waveguide
    left_taper_top = gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.3
    )
    left_taper_top_ref = c << left_taper_top
    left_taper_top_ref.rotate(180)
    left_taper_top_ref.move((-2.0, 0.7))
    
    # Right taper for top waveguide
    right_taper_top = gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.3
    )
    right_taper_top_ref = c << right_taper_top
    right_taper_top_ref.move((2.0, 0.7))
    
    # Left taper for bottom waveguide
    left_taper_bottom = gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.3
    )
    left_taper_bottom_ref = c << left_taper_bottom
    left_taper_bottom_ref.rotate(180)
    left_taper_bottom_ref.move((-2.0, -0.7))
    
    # Right taper for bottom waveguide
    right_taper_bottom = gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.3
    )
    right_taper_bottom_ref = c << right_taper_bottom
    right_taper_bottom_ref.move((2.0, -0.7))
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")