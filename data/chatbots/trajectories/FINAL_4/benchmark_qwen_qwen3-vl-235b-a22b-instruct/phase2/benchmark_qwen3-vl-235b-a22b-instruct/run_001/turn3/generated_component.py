import gdsfactory as gf

@gf.cell
def s_bend_coupler():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a smooth center path that represents the middle between the two waveguides
    # This will create the natural S-bend flow seen in the target
    center_points = [(0, 0), (6, 0), (9, 1.5), (12, 0), (18, 0)]
    center_path = gf.path.smooth(points=center_points, radius=3.0)
    
    # Create the top waveguide by offsetting the center path upward
    top_points = [(x, y + 0.35) for x, y in center_points]
    top_path = gf.path.smooth(points=top_points, radius=3.0)
    wg_top = gf.path.extrude(top_path, cross_section=xs)
    wg_top_ref = c << wg_top
    
    # Create the bottom waveguide by offsetting the center path downward
    bottom_points = [(x, y - 0.35) for x, y in center_points]
    bottom_path = gf.path.smooth(points=bottom_points, radius=3.0)
    wg_bottom = gf.path.extrude(bottom_path, cross_section=xs)
    wg_bottom_ref = c << wg_bottom
    
    # Add ports for connection
    c.add_port("o1", port=wg_top_ref.ports["o1"])
    c.add_port("o2", port=wg_top_ref.ports["o2"])
    c.add_port("o3", port=wg_bottom_ref.ports["o1"])
    c.add_port("o4", port=wg_bottom_ref.ports["o2"])
    
    return c

# Create the device
device = s_bend_coupler()
device.write_gds("s_bend_coupler.gds")