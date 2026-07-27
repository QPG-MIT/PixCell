import gdsfactory as gf

@gf.cell
def racetrack_with_couplers():
    c = gf.Component()
    
    # Define cross-section for waveguides with appropriate minimum bend radius
    # For a small device, we'll set radius_min to a smaller value
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=5.0,  # Set radius to 5.0 µm (reasonable for small devices)
        radius_min=1.0  # Set minimum bend radius to 1.0 µm
    )
    
    # Create the outer racetrack shape using a path
    path = gf.Path()
    path.append(gf.path.straight(length=2.0))
    path.append(gf.path.arc(radius=0.75, angle=180))
    path.append(gf.path.straight(length=2.0))
    path.append(gf.path.arc(radius=0.75, angle=180))
    
    # Extrude the path to create the racetrack
    racetrack = c << gf.path.extrude(path, cross_section=xs)
    
    # Create the two coupling waveguides in the center
    coupling_length = 1.0
    gap_between_waveguides = 0.5
    
    # Create straight waveguides for coupling
    top_coupler = c << gf.components.straight(length=coupling_length, cross_section=xs)
    bottom_coupler = c << gf.components.straight(length=coupling_length, cross_section=xs)
    
    # Position the coupling waveguides
    top_coupler.move((0.5, gap_between_waveguides/2))
    bottom_coupler.move((0.5, -gap_between_waveguides/2))
    
    # Create the rectangular coupling regions (these are wider sections)
    # Use rectangles to create the wider coupling regions
    coupling_width = 0.8
    coupling_height = 0.3
    
    # Create rectangles for the coupling regions
    top_rect1 = c << gf.components.rectangle(size=(coupling_width, coupling_height), layer=(1, 0))
    top_rect2 = c << gf.components.rectangle(size=(coupling_width, coupling_height), layer=(1, 0))
    bottom_rect1 = c << gf.components.rectangle(size=(coupling_width, coupling_height), layer=(1, 0))
    bottom_rect2 = c << gf.components.rectangle(size=(coupling_width, coupling_height), layer=(1, 0))
    
    # Position the rectangles
    top_rect1.move((0.5 - coupling_width/2 - 0.2, gap_between_waveguides/2))
    top_rect2.move((0.5 + coupling_width/2 + 0.2, gap_between_waveguides/2))
    bottom_rect1.move((0.5 - coupling_width/2 - 0.2, -gap_between_waveguides/2))
    bottom_rect2.move((0.5 + coupling_width/2 + 0.2, -gap_between_waveguides/2))
    
    return c

# Create the device
device = racetrack_with_couplers()
device.write_gds("racetrack_with_couplers.gds")