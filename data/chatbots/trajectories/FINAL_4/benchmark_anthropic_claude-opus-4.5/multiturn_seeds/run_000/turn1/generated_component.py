import gdsfactory as gf
import numpy as np

@gf.cell
def tapered_directional_coupler():
    """
    Tapered directional coupler with two waveguides that converge 
    at the center for evanescent coupling, then diverge again.
    
    Footprint: 18 x 3 micrometers
    """
    c = gf.Component()
    
    # Device parameters matching footprint [18, 3]
    length = 18.0  # Total length in um
    waveguide_width = 0.5  # Width of each waveguide
    
    # Vertical positioning
    y_outer = 1.15  # Waveguide center position at input/output ends
    gap_center = 0.1  # Gap between waveguides at coupling region
    y_inner = waveguide_width / 2 + gap_center / 2  # Center position at coupling
    
    # Generate path coordinates
    n_points = 500
    x = np.linspace(0, length, n_points)
    
    # Smooth cosine transition: 1 at x=0 and x=L, 0 at x=L/2
    # This creates the converging-diverging shape
    envelope = (1 + np.cos(2 * np.pi * x / length)) / 2
    
    # Calculate waveguide centerlines
    # Upper waveguide: high at edges, low at center
    y_upper = y_inner + (y_outer - y_inner) * envelope
    # Lower waveguide: mirror of upper
    y_lower = -y_upper
    
    # Create path objects from coordinate arrays
    upper_path = gf.Path(list(zip(x, y_upper)))
    lower_path = gf.Path(list(zip(x, y_lower)))
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))
    
    # Extrude paths to create waveguide geometry
    upper_wg = gf.path.extrude(upper_path, cross_section=xs)
    lower_wg = gf.path.extrude(lower_path, cross_section=xs)
    
    # Add waveguide references to component
    ref_upper = c << upper_wg
    ref_lower = c << lower_wg
    
    # Expose ports for external connections
    c.add_port("o1", port=ref_upper.ports["o1"])  # Upper left input
    c.add_port("o2", port=ref_upper.ports["o2"])  # Upper right output
    c.add_port("o3", port=ref_lower.ports["o1"])  # Lower left input
    c.add_port("o4", port=ref_lower.ports["o2"])  # Lower right output
    
    return c


# Create device and export to GDS
if __name__ == "__main__":
    device = tapered_directional_coupler()
    device.write_gds("tapered_directional_coupler.gds")