import gdsfactory as gf
import numpy as np

@gf.cell
def parametric_device():
    c = gf.Component()
    
    # Device dimensions based on footprint constraint [18, 3] μm
    length = 18.0
    max_height = 3.0
    
    # Thicker bands to match the image
    xs = gf.cross_section.cross_section(width=1.2, layer=(1, 0))
    
    # Vertical offset at edges (narrow points of diamond)
    edge_gap = 0.15
    
    # Create control points for top band (curved upward)
    # Diamond shape: narrow on left, maximum height at center, narrow on right
    n_points = 50
    x_coords = np.linspace(0, length, n_points)
    
    # Use sinusoidal curve for smooth diamond shape
    # Top band: starts low, rises to maximum, returns low
    top_y = edge_gap + (max_height/2 - edge_gap) * np.sin(np.pi * x_coords / length)
    top_points = list(zip(x_coords, top_y))
    
    # Bottom band: mirror of top band
    bottom_y = -edge_gap - (max_height/2 - edge_gap) * np.sin(np.pi * x_coords / length)
    bottom_points = list(zip(x_coords, bottom_y))
    
    # Create paths from the point arrays
    top_path = gf.Path(top_points)
    bottom_path = gf.Path(bottom_points)
    
    # Extrude paths to create the thick curved bands
    top_band = c << gf.path.extrude(top_path, cross_section=xs)
    bottom_band = c << gf.path.extrude(bottom_path, cross_section=xs)
    
    return c

# Create and save the device
device = parametric_device()
device.write_gds("parametric_device.gds")