import gdsfactory as gf

@gf.cell
def y_branch():
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the left straight section (input)
    straight_left_length = 10.0
    wg1_left = c << gf.components.straight(length=straight_left_length, cross_section=xs)
    wg2_left = c << gf.components.straight(length=straight_left_length, cross_section=xs)
    
    # Position the two waveguides parallel to each other
    # Gap between them should be small, let's say 0.5um
    wg2_left.move((0, 1.0))  # Move second waveguide up by 1.0um (center-to-center distance)
    
    # Create Euler bends to separate the waveguides
    bend_radius = 15.0
    bend_angle = 30.0  # degrees
    
    # Create the upper bend
    bend_upper = c << gf.components.bend_euler(radius=bend_radius, angle=bend_angle, cross_section=xs)
    bend_upper.connect("o1", wg1_left.ports["o2"])
    
    # Create the lower bend  
    bend_lower = c << gf.components.bend_euler(radius=bend_radius, angle=-bend_angle, cross_section=xs)
    bend_lower.connect("o1", wg2_left.ports["o2"])
    
    # Create the right straight sections (output)
    straight_right_length = 15.0
    wg1_right = c << gf.components.straight(length=straight_right_length, cross_section=xs)
    wg2_right = c << gf.components.straight(length=straight_right_length, cross_section=xs)
    
    # Connect the bends to the right straight sections
    wg1_right.connect("o1", bend_upper.ports["o2"])
    wg2_right.connect("o1", bend_lower.ports["o2"])
    
    # Add ports for external connections
    c.add_port("o1", port=wg1_left.ports["o1"])
    c.add_port("o2", port=wg2_left.ports["o1"])
    c.add_port("o3", port=wg1_right.ports["o2"])
    c.add_port("o4", port=wg2_right.ports["o2"])
    
    # Flatten the component to resolve off-grid instances
    c.flatten()
    
    return c

# Create and save the device
device = y_branch()
device.write_gds("y_branch.gds")