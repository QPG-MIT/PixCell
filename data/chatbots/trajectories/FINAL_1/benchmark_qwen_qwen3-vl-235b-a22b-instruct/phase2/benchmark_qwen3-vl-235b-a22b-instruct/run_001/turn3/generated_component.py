import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the central waveguide with tapering
    # Start with wider width on left, taper to narrower width on right
    central_taper = c << gf.components.taper(length=40.0, width1=1.0, width2=0.5)
    central_taper.move((0, 0))
    
    # Create top curved waveguide with tapering
    # Use a path with smooth curve and width transition
    top_points = [
        (0, 0.0),      # Start at center
        (10, 0.3),     # Start curving upward
        (20, 0.6),     # Continue curving
        (30, 0.8),     # Continue curving
        (40, 0.85)     # End at top edge
    ]
    
    top_path = gf.Path(top_points)
    
    # Create a transition cross-section that tapers from wider to narrower
    xs_wide = gf.cross_section.cross_section(width=1.0, layer=(1, 0))
    xs_narrow = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    width_transition = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
    
    top_wg = c << gf.path.extrude_transition(top_path, width_transition)
    
    # Create bottom curved waveguide (mirror of top)
    bottom_points = [
        (0, 0.0),      # Start at center
        (10, -0.3),    # Start curving downward
        (20, -0.6),    # Continue curving
        (30, -0.8),    # Continue curving
        (40, -0.85)    # End at bottom edge
    ]
    
    bottom_path = gf.Path(bottom_points)
    bottom_wg = c << gf.path.extrude_transition(bottom_path, width_transition)
    
    # Add ports for connectivity
    c.add_port("o1_top", port=top_wg.ports["o1"])
    c.add_port("o2_top", port=top_wg.ports["o2"])
    c.add_port("o1_central", port=central_taper.ports["o1"])
    c.add_port("o2_central", port=central_taper.ports["o2"])
    c.add_port("o1_bottom", port=bottom_wg.ports["o1"])
    c.add_port("o2_bottom", port=bottom_wg.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")