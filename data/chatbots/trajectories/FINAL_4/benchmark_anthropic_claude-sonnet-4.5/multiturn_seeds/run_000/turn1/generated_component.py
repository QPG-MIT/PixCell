import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_waveguides():
    """
    Creates two parallel waveguides with sinusoidal undulations.
    Matches the 18 x 3 μm footprint constraint.
    """
    c = gf.Component()
    
    # Parameters
    length = 18.0  # μm - horizontal extent
    total_height = 3.0  # μm - vertical extent
    waveguide_width = 0.7  # μm - thickness of each waveguide
    num_waves = 2.0  # number of complete oscillations
    amplitude = 0.28  # amplitude of sinusoidal wave
    
    # Vertical positioning of the two waveguides
    upper_y_center = 0.8  # center position of upper waveguide
    lower_y_center = 2.2  # center position of lower waveguide
    
    # Number of points for smooth curves
    npoints = 400
    
    # Create x coordinates
    x = np.linspace(0, length, npoints)
    
    # Create upper wavy path with sinusoidal variation
    y_upper = upper_y_center + amplitude * np.sin(2 * np.pi * num_waves * x / length)
    points_upper = [(x[i], y_upper[i]) for i in range(npoints)]
    path_upper = gf.Path(points_upper)
    
    # Create lower wavy path with sinusoidal variation (same phase)
    y_lower = lower_y_center + amplitude * np.sin(2 * np.pi * num_waves * x / length)
    points_lower = [(x[i], y_lower[i]) for i in range(npoints)]
    path_lower = gf.Path(points_lower)
    
    # Create cross section for the waveguides
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))
    
    # Extrude paths to create the waveguide components
    wg_upper = path_upper.extrude(xs)
    wg_lower = path_lower.extrude(xs)
    
    # Add waveguides to the component
    c << wg_upper
    c << wg_lower
    
    return c

# Create the device
device = wavy_waveguides()

# Save to GDS file
device.write_gds("wavy_waveguides.gds")

# Display (optional)
device.show()