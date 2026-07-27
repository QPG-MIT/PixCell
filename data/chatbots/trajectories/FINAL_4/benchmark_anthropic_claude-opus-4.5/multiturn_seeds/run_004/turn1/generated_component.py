import gdsfactory as gf
import numpy as np

@gf.cell
def curved_directional_coupler() -> gf.Component:
    """
    Curved directional coupler with smooth sinusoidal coupling profile.
    Two waveguides approach each other in the center and separate at edges.
    
    Footprint: 18 um x 3 um
    """
    c = gf.Component()
    
    # Device parameters matching 18 x 3 um footprint
    length = 18.0  # um - total device length
    wg_width = 0.5  # um - waveguide width
    
    # Coupling geometry
    gap_center = 0.05  # um - minimum gap at coupling point
    y_outer = 1.1  # um - waveguide center offset at edges
    
    # Calculate inner y position from desired gap
    y_inner = (gap_center + wg_width) / 2  # ~0.275 um
    
    # Generate smooth curved path coordinates
    npoints = 200
    x = np.linspace(0, length, npoints)
    
    # Cosine profile for smooth curvature transition
    y_mean = (y_outer + y_inner) / 2
    y_amp = (y_outer - y_inner) / 2
    
    # Top waveguide: starts high, dips in middle, returns high
    y_top = y_mean + y_amp * np.cos(2 * np.pi * x / length)
    # Bottom waveguide: mirror of top (starts low, rises in middle)
    y_bottom = -y_top
    
    # Create path objects from coordinates
    points_top = [(x[i], y_top[i]) for i in range(npoints)]
    points_bottom = [(x[i], y_bottom[i]) for i in range(npoints)]
    
    path_top = gf.Path(points_top)
    path_bottom = gf.Path(points_bottom)
    
    # Define waveguide cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Extrude paths to create waveguide geometry
    wg_top = gf.path.extrude(path_top, cross_section=xs)
    wg_bottom = gf.path.extrude(path_bottom, cross_section=xs)
    
    # Add waveguides to component
    top_ref = c << wg_top
    bottom_ref = c << wg_bottom
    
    # Add ports for connectivity
    c.add_port("o1", port=top_ref.ports["o1"])
    c.add_port("o2", port=top_ref.ports["o2"])
    c.add_port("o3", port=bottom_ref.ports["o1"])
    c.add_port("o4", port=bottom_ref.ports["o2"])
    
    return c


if __name__ == "__main__":
    # Create and save the device
    device = curved_directional_coupler()
    device.write_gds("curved_directional_coupler.gds")