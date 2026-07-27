import gdsfactory as gf

@gf.cell
def s_bend_coupler():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the top waveguide path that crosses from top to bottom
    # Start at (0, 0.5), go to (9, 0), then to (18, -0.5)
    top_points = [(0, 0.5), (6, 0.25), (9, 0), (12, -0.25), (18, -0.5)]
    top_path = gf.path.smooth(points=top_points, radius=3.0)
    wg_top = gf.path.extrude(top_path, cross_section=xs)
    wg_top_ref = c << wg_top
    
    # Create the bottom waveguide path that crosses from bottom to top
    # Start at (0, -0.5), go to (9, 0), then to (18, 0.5)
    bottom_points = [(0, -0.5), (6, -0.25), (9, 0), (12, 0.25), (18, 0.5)]
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