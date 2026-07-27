import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create two separate waveguide paths
    # Upper waveguide path
    upper_path = gf.path.straight(length=20)  # Left extension
    upper_path = upper_path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend up
    upper_path = upper_path.append(gf.path.straight(length=2))  # Vertical section
    upper_path = upper_path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right
    upper_path = upper_path.append(gf.path.straight(length=80))  # Straight section
    upper_path = upper_path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend down
    upper_path = upper_path.append(gf.path.straight(length=2))  # Vertical section
    upper_path = upper_path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right
    upper_path = upper_path.append(gf.path.straight(length=20))  # Right extension
    
    # Lower waveguide path
    lower_path = gf.path.straight(length=20)  # Left extension
    lower_path = lower_path.append(gf.path.euler(radius=10, angle=-90, p=0.5))  # Bend down
    lower_path = lower_path.append(gf.path.straight(length=2))  # Vertical section
    lower_path = lower_path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right
    lower_path = lower_path.append(gf.path.straight(length=80))  # Straight section
    lower_path = lower_path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend up
    lower_path = lower_path.append(gf.path.straight(length=2))  # Vertical section
    lower_path = lower_path.append(gf.path.euler(radius=10, angle=90, p=0.5))  # Bend right
    lower_path = lower_path.append(gf.path.straight(length=20))  # Right extension
    
    # Extrude the paths to create the waveguides
    upper_waveguide = gf.path.extrude(upper_path, cross_section=xs)
    lower_waveguide = gf.path.extrude(lower_path, cross_section=xs)
    
    # Add the waveguides to the component
    upper_ref = c << upper_waveguide
    lower_ref = c << lower_waveguide
    
    # Position the lower waveguide below the upper one
    lower_ref.move((0, -10))  # Adjust this value to match the desired spacing
    
    # Expose ports for the device
    c.add_port("input_upper", port=upper_ref.ports["o1"])
    c.add_port("output_upper", port=upper_ref.ports["o2"])
    c.add_port("input_lower", port=lower_ref.ports["o1"])
    c.add_port("output_lower", port=lower_ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")