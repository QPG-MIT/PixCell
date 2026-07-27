import gdsfactory as gf

@gf.cell
def parametric_device():
    c = gf.Component()
    
    # Define cross-section for the curved bands
    # The bands appear quite thick in the image
    xs = gf.cross_section.cross_section(width=0.6, layer=(1, 0))
    
    # Device dimensions based on footprint constraint [18, 3] μm
    length = 18.0
    max_separation = 3.0
    
    # Starting/ending positions (close together at edges)
    edge_offset = 0.3
    
    # Create smooth curved path for top band
    # It starts near center-left, bows upward in middle, returns to center-right
    top_points = [
        (0, edge_offset),
        (length * 0.5, max_separation * 0.45),  # Peak at middle
        (length, edge_offset)
    ]
    
    # Create smooth curved path for bottom band
    # Mirror of top band - bows downward
    bottom_points = [
        (0, -edge_offset),
        (length * 0.5, -max_separation * 0.45),  # Trough at middle
        (length, -edge_offset)
    ]
    
    # Create smooth paths with appropriate bend radius
    top_path = gf.path.smooth(top_points, radius=4.0)
    bottom_path = gf.path.smooth(bottom_points, radius=4.0)
    
    # Extrude paths to create the curved bands
    top_band = c << gf.path.extrude(top_path, cross_section=xs)
    bottom_band = c << gf.path.extrude(bottom_path, cross_section=xs)
    
    return c

# Create and save the device
device = parametric_device()
device.write_gds("parametric_device.gds")