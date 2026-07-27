import gdsfactory as gf
import numpy as np

@gf.cell
def create_device():
    """
    Creates a waveguide crossing structure with two smooth waveguides
    forming an hourglass/bowtie pattern.
    """
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Device parameters
    total_length = 120  # Total device length in um
    total_height = 4    # Total device height in um
    
    # Vertical positions
    y_top = 1.5      # Top waveguide vertical position at ends
    y_bottom = -1.5  # Bottom waveguide vertical position at ends
    
    # Create smooth paths using waypoints
    num_points = 100
    x = np.linspace(0, total_length, num_points)
    
    # Top waveguide: starts high, dips down in middle, goes back up
    # Use a smooth sinusoidal-like curve
    y_top_path = y_top - y_top * np.sin(np.pi * x / total_length)**2
    
    # Bottom waveguide: starts low, rises up in middle, goes back down
    # Mirror of top waveguide
    y_bottom_path = y_bottom + abs(y_bottom) * np.sin(np.pi * x / total_length)**2
    
    # Create paths from points
    top_points = list(zip(x, y_top_path))
    bottom_points = list(zip(x, y_bottom_path))
    
    top_path = gf.Path(top_points)
    bottom_path = gf.Path(bottom_points)
    
    # Extrude paths to create waveguides
    top_wg = c << gf.path.extrude(top_path, cross_section=xs)
    bottom_wg = c << gf.path.extrude(bottom_path, cross_section=xs)
    
    return c

# Create the device and save to GDS
device = create_device()
device.write_gds("waveguide_crossing.gds")

# Optional: display the device
device.show()