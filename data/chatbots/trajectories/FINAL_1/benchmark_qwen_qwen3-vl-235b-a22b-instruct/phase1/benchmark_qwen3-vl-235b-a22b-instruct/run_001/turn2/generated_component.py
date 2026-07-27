import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create central straight waveguide
    central_wg = c << gf.components.straight(length=40.0, cross_section=xs)
    central_wg.move((0, 0))
    
    # Create top curved waveguide using a custom path with more control points
    # Start at (0, 0.4) to leave space from center, end at (40, 0.85) for 1.7um total height
    top_points = [
        (0, 0.4),      # Start position (slightly offset from center)
        (10, 0.4),     # Continue straight for a bit
        (20, 0.6),     # Start curving upward
        (30, 0.75),    # Continue curving
        (40, 0.85)     # End at top edge (1.7um total height / 2 = 0.85um)
    ]
    
    top_path = gf.Path(top_points)
    top_wg = c << gf.path.extrude(top_path, cross_section=xs)
    
    # Create bottom curved waveguide (mirror of top)
    bottom_points = [
        (0, -0.4),     # Start position (slightly offset from center)
        (10, -0.4),    # Continue straight for a bit
        (20, -0.6),    # Start curving downward
        (30, -0.75),   # Continue curving
        (40, -0.85)    # End at bottom edge
    ]
    
    bottom_path = gf.Path(bottom_points)
    bottom_wg = c << gf.path.extrude(bottom_path, cross_section=xs)
    
    # Add ports for connectivity
    c.add_port("o1_top", port=top_wg.ports["o1"])
    c.add_port("o2_top", port=top_wg.ports["o2"])
    c.add_port("o1_central", port=central_wg.ports["o1"])
    c.add_port("o2_central", port=central_wg.ports["o2"])
    c.add_port("o1_bottom", port=bottom_wg.ports["o1"])
    c.add_port("o2_bottom", port=bottom_wg.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")