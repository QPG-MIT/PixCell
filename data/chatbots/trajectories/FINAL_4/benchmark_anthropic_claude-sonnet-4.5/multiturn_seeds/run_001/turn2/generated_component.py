import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_waveguides():
    """
    Creates two parallel waveguides with sinusoidal undulation.
    The waveguides oscillate in phase (together).
    """
    c = gf.Component()
    
    # Device parameters matching footprint [18, 3] µm
    length = 18.0          # Total length in µm
    height = 3.0           # Total height in µm
    wg_width = 0.55        # Width of each waveguide
    num_periods = 3.0      # Number of wave cycles
    amplitude = 0.5        # Oscillation amplitude
    
    # Generate smooth sinusoidal paths
    npoints = 500  # High point count for smooth curves
    x = np.linspace(0, length, npoints)
    
    # Both waveguides oscillate with the SAME phase
    # Top waveguide - oscillates around y = 2.25 µm
    y_top = 2.25 + amplitude * np.sin(2 * np.pi * num_periods * x / length)
    
    # Bottom waveguide - oscillates around y = 0.75 µm with SAME phase
    y_bottom = 0.75 + amplitude * np.sin(2 * np.pi * num_periods * x / length)
    
    # Create paths from coordinate arrays
    path_top = gf.Path(list(zip(x, y_top)))
    path_bottom = gf.Path(list(zip(x, y_bottom)))
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Extrude paths to create waveguide components
    wg_top = c << gf.path.extrude(path_top, cross_section=xs)
    wg_bottom = c << gf.path.extrude(path_bottom, cross_section=xs)
    
    return c

# Create device and save to GDS
device = wavy_waveguides()
device.write_gds("wavy_waveguides.gds")
print("Device created successfully!")
print(f"Bounding box: {device.bbox}")