import gdsfactory as gf
import numpy as np

@gf.cell
def curved_coupler():
    """
    Curved directional coupler with two waveguides that curve toward
    each other in the center to create a coupling region.
    
    Footprint: 18 um (length) x 3 um (height)
    """
    c = gf.Component()
    
    # Device geometry parameters based on footprint [18, 3] um
    total_length = 18.0  # um
    waveguide_width = 0.65  # um - slightly thicker waveguides
    
    # Waveguide centerline y-positions
    # At edges: waveguides at outer positions (max separation)
    # At center: waveguides come close together (min separation)
    y_outer = 1.1   # centerline y-position at left/right edges
    y_inner = 0.38  # centerline y-position at center (smaller gap)
    
    # Smooth cosine curve parameters
    y_avg = (y_outer + y_inner) / 2
    y_amp = (y_outer - y_inner) / 2
    
    # Generate path coordinates using cosine function for smooth curves
    n_points = 200
    x = np.linspace(0, total_length, n_points)
    
    # Top waveguide path: high at edges, dips down in middle
    y_top = y_avg + y_amp * np.cos(2 * np.pi * x / total_length)
    
    # Bottom waveguide path: mirror of top (low at edges, rises in middle)
    y_bottom = -y_top
    
    # Create Path objects from coordinate points
    path_top = gf.Path(list(zip(x, y_top)))
    path_bottom = gf.Path(list(zip(x, y_bottom)))
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))
    
    # Extrude paths to create waveguide geometry
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bottom, cross_section=xs)
    
    return c


if __name__ == "__main__":
    device = curved_coupler()
    device.write_gds("curved_coupler.gds")