import gdsfactory as gf

@gf.cell
def y_branch():
    c = gf.Component()
    
    # Define cross-section (0.5um wide waveguide on layer (1,0))
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # === Create a smooth Y-branch using path system ===
    # Start with a straight path for the input
    path = gf.path.straight(length=10.0)
    
    # Create a smooth Y-branch by adding two diverging paths
    # We'll use a smooth path with waypoints to create the Y-branch
    # Start point, then diverge to two endpoints
    
    # Define the divergence points
    divergence_length = 15.0
    divergence_angle = 25.0  # degrees
    
    # Create the Y-branch path
    # Start with straight section
    path = gf.path.straight(length=10.0)
    
    # Create the diverging paths using smooth path with waypoints
    # We'll create a path that starts straight, then smoothly diverges
    # using a smooth curve with control points
    
    # Create a smooth Y-branch by defining control points
    # Start point, then two endpoints for the diverging branches
    start_point = (0, 0)
    upper_end_point = (divergence_length, divergence_length * 0.2)
    lower_end_point = (divergence_length, -divergence_length * 0.2)
    
    # Create the upper branch path
    upper_path = gf.Path()
    upper_path.append(gf.path.straight(length=10.0))  # input straight
    upper_path.append(gf.path.euler(radius=15.0, angle=divergence_angle))  # upper bend
    upper_path.append(gf.path.straight(length=15.0))  # upper output straight
    
    # Create the lower branch path
    lower_path = gf.Path()
    lower_path.append(gf.path.straight(length=10.0))  # input straight
    lower_path.append(gf.path.euler(radius=15.0, angle=-divergence_angle))  # lower bend
    lower_path.append(gf.path.straight(length=15.0))  # lower output straight
    
    # Create the Y-branch by combining the paths
    # We need to create a single continuous path for the Y-branch
    # Use a smooth path with waypoints to create the Y-branch
    
    # Create a smooth Y-branch using a single path with waypoints
    # Start at (0,0), go to (10,0), then diverge to two endpoints
    
    # Create the Y-branch using a smooth path
    y_path = gf.Path()
    y_path.append(gf.path.straight(length=10.0))  # input straight
    
    # Create the divergence using a smooth transition
    # We'll use a bezier curve to create a smooth Y-branch
    control_points = [
        (10, 0),  # start of divergence
        (15, 5),  # control point for upper branch
        (20, 10),  # end of upper branch
        (15, -5),  # control point for lower branch
        (20, -10)  # end of lower branch
    ]
    
    # Create the Y-branch using two separate paths for upper and lower branches
    # This will create a more natural Y-branch shape
    
    # Create upper branch
    upper_branch = gf.Component()
    upper_path = gf.Path()
    upper_path.append(gf.path.straight(length=10.0))  # input straight
    upper_path.append(gf.path.euler(radius=15.0, angle=25.0))  # upper bend
    upper_path.append(gf.path.straight(length=15.0))  # upper output straight
    upper_component = gf.path.extrude(upper_path, cross_section=xs)
    upper_ref = upper_branch << upper_component
    
    # Create lower branch
    lower_branch = gf.Component()
    lower_path = gf.Path()
    lower_path.append(gf.path.straight(length=10.0))  # input straight
    lower_path.append(gf.path.euler(radius=15.0, angle=-25.0))  # lower bend
    lower_path.append(gf.path.straight(length=15.0))  # lower output straight
    lower_component = gf.path.extrude(lower_path, cross_section=xs)
    lower_ref = lower_branch << lower_component
    
    # Add both branches to the main component
    c << upper_branch
    c << lower_branch
    
    # Add ports
    c.add_port("o1", port=upper_ref.ports["o1"])  # Input port (same for both branches)
    c.add_port("o2", port=upper_ref.ports["o2"])  # Upper output
    c.add_port("o3", port=lower_ref.ports["o2"])  # Lower output
    
    # Flatten to avoid off-grid instance errors
    c.flatten()
    
    return c

# Create and save the device
device = y_branch()
device.write_gds("y_branch.gds")