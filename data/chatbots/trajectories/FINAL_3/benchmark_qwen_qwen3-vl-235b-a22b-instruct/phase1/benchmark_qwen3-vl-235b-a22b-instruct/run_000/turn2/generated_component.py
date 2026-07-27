import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a path for the entire structure
    # Start at the left end of the top waveguide
    path = gf.path.straight(length=20)  # Left extension of top waveguide
    
    # Add the right S-bend for the top waveguide
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend down
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right
    
    # Add the straight section for the top waveguide
    path = path.append(gf.path.straight(length=80))  # Straight section
    
    # Add the left S-bend for the top waveguide (mirrored)
    path = path.append(gf.path.euler(radius=10, angle=-90, p=0.5))  # Bend up
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=-90, p=0.5))  # Bend left
    
    # Add the right extension of the top waveguide
    path = path.append(gf.path.straight(length=20))  # Right extension
    
    # Now create the bottom waveguide path
    path_bottom = gf.path.straight(length=20)  # Left extension of bottom waveguide
    
    # Add the right S-bend for the bottom waveguide
    path_bottom = path_bottom.append(gf.path.euler(radius=10, angle=-90, p=0.5))  # Bend up
    path_bottom = path_bottom.append(gf.path.straight(length=2))  # Vertical section
    path_bottom = path_bottom.append(gf.path.euler(radius=10, angle=-90, p=0.5))  # Bend right
    
    # Add the straight section for the bottom waveguide
    path_bottom = path_bottom.append(gf.path.straight(length=80))  # Straight section
    
    # Add the left S-bend for the bottom waveguide (mirrored)
    path_bottom = path_bottom.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend down
    path_bottom = path_bottom.append(gf.path.straight(length=2))  # Vertical section
    path_bottom = path_bottom.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend left
    
    # Add the right extension of the bottom waveguide
    path_bottom = path_bottom.append(gf.path.straight(length=20))  # Right extension
    
    # Extrude the paths to create waveguides
    waveguide_top = gf.path.extrude(path, cross_section=xs)
    waveguide_bottom = gf.path.extrude(path_bottom, cross_section=xs)
    
    # Add the waveguides to the component
    ref_top = c << waveguide_top
    ref_bottom = c << waveguide_bottom
    
    # Position the bottom waveguide below the top one
    ref_bottom.movey(-4.0)
    
    # Expose ports for the device
    c.add_port("input_top", port=ref_top.ports["o1"])
    c.add_port("output_top", port=ref_top.ports["o2"])
    c.add_port("input_bottom", port=ref_bottom.ports["o1"])
    c.add_port("output_bottom", port=ref_bottom.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")