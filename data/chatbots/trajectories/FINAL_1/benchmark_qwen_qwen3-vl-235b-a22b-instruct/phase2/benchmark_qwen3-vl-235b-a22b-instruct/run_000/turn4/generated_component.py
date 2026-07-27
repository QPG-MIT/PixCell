import gdsfactory as gf

@gf.cell
def y_branch():
    c = gf.Component()
    
    # Define cross-section (0.5um wide waveguide on layer (1,0))
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the input section
    input_section = gf.components.straight(length=10.0, cross_section=xs)
    input_ref = c << input_section
    
    # Create the upper branch
    upper_path = gf.Path()
    upper_path.append(gf.path.euler(radius=15.0, angle=25.0))  # upper bend
    upper_path.append(gf.path.straight(length=15.0))  # upper output straight
    upper_component = gf.path.extrude(upper_path, cross_section=xs)
    upper_ref = c << upper_component
    
    # Create the lower branch
    lower_path = gf.Path()
    lower_path.append(gf.path.euler(radius=15.0, angle=-25.0))  # lower bend
    lower_path.append(gf.path.straight(length=15.0))  # lower output straight
    lower_component = gf.path.extrude(lower_path, cross_section=xs)
    lower_ref = c << lower_component
    
    # Connect the branches to the input section
    # We need to ensure we're connecting the correct ports
    # Let's get the ports by their orientation
    
    # Connect upper branch to input section
    # Find the port on the upper branch that's at the start of the path
    upper_start_port = None
    for port_name, port in upper_ref.ports.items():
        if abs(port.orientation) < 10:  # approximately 0 degrees (start of path)
            upper_start_port = port
            break
    
    # Connect lower branch to input section
    lower_start_port = None
    for port_name, port in lower_ref.ports.items():
        if abs(port.orientation) < 10:  # approximately 0 degrees (start of path)
            lower_start_port = port
            break
    
    # Connect to the output port of the input section
    input_output_port = input_ref.ports["o2"]
    
    # Connect the branches
    if upper_start_port:
        upper_ref.connect(upper_start_port.name, input_output_port)
    if lower_start_port:
        lower_ref.connect(lower_start_port.name, input_output_port)
    
    # Add ports to the main component
    c.add_port("o1", port=input_ref.ports["o1"])  # Input port
    
    # Find the output ports (approximately 180 degrees for upper branch, 0 degrees for lower branch)
    upper_output_port = None
    for port_name, port in upper_ref.ports.items():
        if abs(port.orientation - 180) < 10:  # approximately 180 degrees (end of path)
            upper_output_port = port
            break
    
    lower_output_port = None
    for port_name, port in lower_ref.ports.items():
        if abs(port.orientation) < 10:  # approximately 0 degrees (end of path)
            lower_output_port = port
            break
    
    if upper_output_port:
        c.add_port("o2", port=upper_output_port)  # Upper output
    if lower_output_port:
        c.add_port("o3", port=lower_output_port)  # Lower output
    
    # Flatten to avoid off-grid instance errors
    c.flatten()
    
    return c

# Create and save the device
device = y_branch()
device.write_gds("y_branch.gds")