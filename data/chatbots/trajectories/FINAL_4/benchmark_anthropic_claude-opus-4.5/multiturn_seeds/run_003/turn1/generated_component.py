import gdsfactory as gf
import numpy as np

@gf.cell
def sinusoidal_pinch_coupler(
    length: float = 18.0,
    width: float = 0.6,
    gap_min: float = 0.1,
    gap_max: float = 1.8,
    layer: tuple = (1, 0),
    n_points: int = 200,
):
    """
    Creates a symmetric coupler where two waveguides follow sinusoidal
    paths, forming an eye-shaped gap. The waveguides pinch close together
    at the center and spread apart at the edges.
    
    Footprint: 18 um x 3 um
    """
    c = gf.Component()
    
    # Generate x coordinates along device length
    x = np.linspace(0, length, n_points)
    
    # Center-to-center separation at edges and center
    sep_edge = gap_max + width
    sep_center = gap_min + width
    
    # Waveguide centerline y-positions at edges vs center
    y_edge = sep_edge / 2
    y_center = sep_center / 2
    
    # Sinusoidal y-profile: starts at y_edge, dips to y_center at middle
    y_mean = (y_edge + y_center) / 2
    y_amp = (y_edge - y_center) / 2
    y_top = y_mean + y_amp * np.cos(2 * np.pi * x / length)
    y_bottom = -y_top  # Symmetric about x-axis
    
    # Create path objects from point lists
    path_top = gf.Path([(float(xi), float(yi)) for xi, yi in zip(x, y_top)])
    path_bottom = gf.Path([(float(xi), float(yi)) for xi, yi in zip(x, y_bottom)])
    
    # Define waveguide cross-section
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    
    # Extrude paths to create waveguide geometry
    wg_top = gf.path.extrude(path_top, cross_section=xs)
    wg_bottom = gf.path.extrude(path_bottom, cross_section=xs)
    
    # Add to component
    top_ref = c << wg_top
    bottom_ref = c << wg_bottom
    
    # Add ports for external connectivity
    c.add_port("o1_top", port=top_ref.ports["o1"])
    c.add_port("o2_top", port=top_ref.ports["o2"])
    c.add_port("o1_bottom", port=bottom_ref.ports["o1"])
    c.add_port("o2_bottom", port=bottom_ref.ports["o2"])
    
    return c


# Generate and save the device
device = sinusoidal_pinch_coupler()
device.write_gds("sinusoidal_pinch_coupler.gds")