import gdsfactory as gf

@gf.cell
def s_bend_coupler():
    c = gf.Component()
    
    # Create an S-bend path
    # Using the path system to create a smooth S-bend
    points = [(0, 0), (6, 1.5), (12, -1.5), (18, 0)]
    path = gf.path.smooth(points=points, radius=2.0)
    
    # Define cross-section for a single waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Extrude the path to create the first waveguide
    wg1 = gf.path.extrude(path, cross_section=xs)
    wg1_ref = c << wg1
    
    # Create the second waveguide by offsetting the path vertically
    # We need to create a new path that is offset vertically
    points2 = [(0, -0.7), (6, 0.8), (12, -2.2), (18, -0.7)]  # Offset by 0.7μm down
    path2 = gf.path.smooth(points=points2, radius=2.0)
    wg2 = gf.path.extrude(path2, cross_section=xs)
    wg2_ref = c << wg2
    
    # Add ports for connection
    c.add_port("o1", port=wg1_ref.ports["o1"])
    c.add_port("o2", port=wg1_ref.ports["o2"])
    c.add_port("o3", port=wg2_ref.ports["o1"])
    c.add_port("o4", port=wg2_ref.ports["o2"])
    
    return c

# Create the device
device = s_bend_coupler()
device.write_gds("s_bend_coupler.gds")