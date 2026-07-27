import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_parallel_waveguides():
    """Creates two parallel sinusoidal waveguides"""
    c = gf.Component()
    
    # Device parameters matching footprint
    length = 18.0  # μm
    total_height = 3.0  # μm
    
    # Wave parameters
    num_points = 400  # smooth curves
    num_periods = 2.5  # number of complete oscillations
    amplitude = 0.35  # amplitude of sine wave
    
    # Waveguide parameters
    wg_width = 0.55  # width of each band
    separation = 1.1  # vertical separation between centerlines
    
    # Create x coordinates
    x = np.linspace(0, length, num_points)
    
    # Create sinusoidal modulation (both waveguides follow same pattern)
    y_modulation = amplitude * np.sin(2 * np.pi * num_periods * x / length)
    
    # Top waveguide path
    y_top = total_height/2 + separation/2 + y_modulation
    points_top = np.column_stack([x, y_top])
    path_top = gf.Path(points_top)
    
    # Bottom waveguide path
    y_bottom = total_height/2 - separation/2 + y_modulation
    points_bottom = np.column_stack([x, y_bottom])
    path_bottom = gf.Path(points_bottom)
    
    # Create cross-section for waveguides
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Extrude paths to create waveguide components
    wg_top = gf.path.extrude(path_top, cross_section=xs)
    wg_bottom = gf.path.extrude(path_bottom, cross_section=xs)
    
    # Add waveguides to main component
    c << wg_top
    c << wg_bottom
    
    return c

# Create the device
device = wavy_parallel_waveguides()

# Save to GDS file
device.write_gds("wavy_parallel_waveguides.gds")

# Display the device
device.show()