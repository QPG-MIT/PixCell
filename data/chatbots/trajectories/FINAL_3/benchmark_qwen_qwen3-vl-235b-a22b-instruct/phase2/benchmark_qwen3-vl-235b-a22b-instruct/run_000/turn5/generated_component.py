import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a single continuous path for the figure 8 pattern
    # Start with left extension
    path = gf.path.straight(length=20)
    
    # First loop (top half of figure 8)
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend up
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right
    path = path.append(gf.path.straight(length=80))  # Straight section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend down
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right (completing top loop)
    
    # Second loop (bottom half of figure 8) - continue from current position
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend down
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend left
    path = path.append(gf.path.straight(length=80))  # Straight section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend up
    path = path.append(gf.path.straight(length=2))  # Vertical section
    path = path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend left (completing bottom loop)
    
    # Right extension
    path = path.append(gf.path.straight(length=20))
    
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