import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the main structure that will split into three branches
    # Start with a wider section on the left that tapers to the right
    
    # Create a path that represents the centerline of the entire structure
    # This will be a single path that splits into three branches
    
    # Create the main path that will form the center branch
    central_points = [
        (0, 0.0),      # Start at center, wide section
        (10, 0.0),     # Continue straight
        (20, 0.0),     # Continue straight
        (30, 0.0),     # Continue straight
        (40, 0.0)      # End at right
    ]
    
    central_path = gf.Path(central_points)
    
    # Create a transition cross-section that tapers from wider to narrower
    xs_wide = gf.cross_section.cross_section(width=1.7, layer=(1, 0))  # Wider on left
    xs_narrow = gf.cross_section.cross_section(width=0.5, layer=(1, 0))  # Narrower on right
    width_transition = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
    
    # Create the main tapered structure (center branch)
    main_structure = c << gf.path.extrude_transition(central_path, width_transition)
    
    # Create the top branch that emerges from the main structure
    # This should start from the same point as the main structure and curve upward
    top_branch_points = [
        (0, 0.0),      # Start from the same point as main structure
        (10, 0.2),     # Start curving upward
        (20, 0.4),     # Continue curving upward
        (30, 0.6),     # Continue curving
        (40, 0.85)     # End at top edge
    ]
    
    top_branch_path = gf.Path(top_branch_points)
    top_branch = c << gf.path.extrude_transition(top_branch_path, width_transition)
    
    # Create the bottom branch that emerges from the main structure
    # This should start from the same point as the main structure and curve downward
    bottom_branch_points = [
        (0, 0.0),      # Start from the same point as main structure
        (10, -0.2),    # Start curving downward
        (20, -0.4),    # Continue curving downward
        (30, -0.6),    # Continue curving
        (40, -0.85)    # End at bottom edge
    ]
    
    bottom_branch_path = gf.Path(bottom_branch_points)
    bottom_branch = c << gf.path.extrude_transition(bottom_branch_path, width_transition)
    
    # Add ports for connectivity
    c.add_port("o1_main", port=main_structure.ports["o1"])
    c.add_port("o2_main", port=main_structure.ports["o2"])
    c.add_port("o1_top", port=top_branch.ports["o1"])
    c.add_port("o2_top", port=top_branch.ports["o2"])
    c.add_port("o1_bottom", port=bottom_branch.ports["o1"])
    c.add_port("o2_bottom", port=bottom_branch.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")