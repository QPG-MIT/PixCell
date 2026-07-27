import gdsfactory as gf

@gf.cell
def y_junction():
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the Y-junction using paths
    # Start with a straight path for the input
    input_path = gf.path.straight(length=30)
    
    # Create the two output paths with curves
    # Use Euler bends for smooth transitions
    bend_angle = 30  # Angle for the Y-junction branches
    
    # Create path for top output
    top_output_path = gf.path.euler(radius=20, angle=bend_angle)
    top_output_path = top_output_path.append(gf.path.straight(length=60))
    
    # Create path for bottom output
    bottom_output_path = gf.path.euler(radius=20, angle=-bend_angle)
    bottom_output_path = bottom_output_path.append(gf.path.straight(length=60))
    
    # Create components from paths
    input_wg = c << gf.path.extrude(input_path, cross_section=xs)
    top_output_wg = c << gf.path.extrude(top_output_path, cross_section=xs)
    bottom_output_wg = c << gf.path.extrude(bottom_output_path, cross_section=xs)
    
    # Position the components
    # Place input waveguide
    input_wg.move((0, 0))
    
    # Position top output waveguide
    # Connect the start of top output to end of input
    top_output_wg.connect("o1", input_wg.ports["o2"])
    
    # Position bottom output waveguide
    # Connect the start of bottom output to end of input
    bottom_output_wg.connect("o1", input_wg.ports["o2"])
    
    # Expose ports
    c.add_port("o1", port=input_wg.ports["o1"])
    c.add_port("o2_top", port=top_output_wg.ports["o2"])
    c.add_port("o2_bottom", port=bottom_output_wg.ports["o2"])
    
    return c

# Create and save the device
device = y_junction()
device.write_gds("y_junction.gds")