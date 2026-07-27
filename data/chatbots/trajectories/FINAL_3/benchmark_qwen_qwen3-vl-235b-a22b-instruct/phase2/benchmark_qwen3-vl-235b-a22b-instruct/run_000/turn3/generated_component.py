import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a single continuous path that matches the target image
    # Start at the left end
    path = gf.path.straight(length=20)  # Left extension
    
    # First bend: up and right
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend up
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right
    
    # Straight section
    path = path.append(gf.path.straight(length=80))  # Straight section
    
    # Second bend: down and right
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend down
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right
    
    # Straight section
    path = path.append(gf.path.straight(length=80))  # Straight section
    
    # Third bend: up and left
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend up
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend left
    
    # Straight section
    path = path.append(gf.path.straight(length=80))  # Straight section
    
    # Fourth bend: down and left
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend down
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend left
    
    # Add the right extension
    path = path.append(gf.path.straight(length=20))  # Right extension
    
    # Extrude the path to create the waveguide
    waveguide = gf.path.extrude(path, cross_section=xs)
    
    # Add the waveguide to the component
    ref = c << waveguide
    
    # Expose ports for the device
    c.add_port("input", port=ref.ports["o1"])
    c.add_port("output", port=ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")