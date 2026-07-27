import gdsfactory as gf

@gf.cell
def create_s_shaped_grating_device():
    c = gf.Component()
    
    # Create a cross-section with appropriate minimum radius
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=5.0,
        radius_min=3.0
    )
    
    # Create the S-shaped path with more gradual curves
    s_path = gf.Path()
    s_path.append(gf.path.straight(length=1.0))  # Start straight section
    s_path.append(gf.path.euler(radius=8.0, angle=90))  # First curve
    s_path.append(gf.path.straight(length=12.0))  # Middle straight section
    s_path.append(gf.path.euler(radius=8.0, angle=-90))  # Second curve
    s_path.append(gf.path.straight(length=1.0))  # End straight section
    
    # Extrude the S-shaped path
    s_waveguide = c << gf.path.extrude(s_path, cross_section=xs)
    
    # Add gratings along the S-shaped waveguide
    tooth_width = 0.1
    tooth_height = 0.3
    tooth_spacing = 0.2
    
    # Calculate number of teeth based on the middle straight section
    middle_length = 12.0
    num_teeth = int(middle_length / (tooth_width + tooth_spacing)) - 2
    
    # Add teeth perpendicular to the waveguide (extending outward from both sides)
    for i in range(num_teeth):
        # Calculate position along the middle straight section
        tooth_x = s_waveguide.xmin + 1.0 + tooth_width/2 + i * (tooth_width + tooth_spacing)
        tooth_y = s_waveguide.ymin  # Position at bottom of waveguide
        
        # Create tooth extending downward (from bottom of waveguide)
        lower_tooth = c << gf.components.rectangle(
            size=(tooth_width, tooth_height), 
            layer=(1, 0), 
            centered=False
        )
        lower_tooth.move((tooth_x, tooth_y - tooth_height))
        
        # Create tooth extending upward (from top of waveguide)
        upper_tooth = c << gf.components.rectangle(
            size=(tooth_width, tooth_height), 
            layer=(1, 0), 
            centered=False
        )
        upper_tooth.move((tooth_x, s_waveguide.ymax))
    
    # Add tapers to the ends of the S-waveguide
    taper_length = 2.0
    
    # Top taper (input) - at the start of the S-waveguide
    top_taper = c << gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.1
    )
    # Position at start of S-waveguide
    top_taper.move((s_waveguide.xmin - taper_length, s_waveguide.ymin))
    top_taper.rotate(180)  # Point inward
    
    # Bottom taper (output) - at the end of the S-waveguide
    bottom_taper = c << gf.components.taper(
        length=taper_length, 
        width1=0.5, 
        width2=0.1
    )
    # Position at end of S-waveguide
    bottom_taper.move((s_waveguide.xmax, s_waveguide.ymin))
    bottom_taper.rotate(0)  # Point outward
    
    return c

# Create and save the device
device = create_s_shaped_grating_device()
device.write_gds("s_shaped_grating_device.gds")