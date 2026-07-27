import gdsfactory as gf

@gf.cell
def create_cross_petal_device_v3():
    c = gf.Component()
    layer = (1, 0)
    
    # Define size parameters based on 4.7μm footprint
    total_size = 4.7  # μm
    
    # Create a cross-section for the path
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Create a path that traces the outline of the 4-lobed shape
    # Using control points to create smooth curves
    path_points = [
        (0, total_size/2),  # Top point
        (total_size/4, total_size/4),  # Top-right curve
        (total_size/2, 0),  # Right point
        (total_size/4, -total_size/4),  # Bottom-right curve
        (0, -total_size/2),  # Bottom point
        (-total_size/4, -total_size/4),  # Bottom-left curve
        (-total_size/2, 0),  # Left point
        (-total_size/4, total_size/4),  # Top-left curve
        (0, total_size/2)  # Back to top (close path)
    ]
    
    # Create the path
    path = gf.path.smooth(points=path_points, radius=total_size/8)
    
    # Extrude the path to create the component
    petal_shape = c << gf.path.extrude(path, cross_section=xs)
    
    # Add ports at the natural endpoints of each lobe
    # Top port
    c.add_port("o1", center=(0, total_size/2), width=0.5, orientation=90, layer=layer)
    # Bottom port
    c.add_port("o2", center=(0, -total_size/2), width=0.5, orientation=270, layer=layer)
    # Right port
    c.add_port("o3", center=(total_size/2, 0), width=0.5, orientation=0, layer=layer)
    # Left port
    c.add_port("o4", center=(-total_size/2, 0), width=0.5, orientation=180, layer=layer)
    
    return c

# Create and save the device
device = create_cross_petal_device_v3()
device.write_gds("cross_petal_device_v3.gds")