import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides (narrow, ~0.5um width based on footprint)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create central straight waveguide
    central_wg = c << gf.components.straight(length=40.0, cross_section=xs)
    central_wg.move((0, 0))
    
    # Create top curved waveguide
    # Start with a smooth path that goes straight then curves upward
    top_path = gf.path.smooth(
        points=[(0, 0.85), (20, 0.85), (40, 1.7)], 
        radius=5.0
    )
    top_wg = c << gf.path.extrude(top_path, cross_section=xs)
    
    # Create bottom curved waveguide (mirror of top)
    bottom_path = gf.path.smooth(
        points=[(0, -0.85), (20, -0.85), (40, -1.7)], 
        radius=5.0
    )
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