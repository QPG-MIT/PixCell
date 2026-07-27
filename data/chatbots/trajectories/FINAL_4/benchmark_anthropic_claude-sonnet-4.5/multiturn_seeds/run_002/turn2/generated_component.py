import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_parallel_waveguides():
    """Creates two parallel sinusoidal waveguides with opposite phase"""
    c = gf.Component()
    
    # Device parameters matching footprint
    length = 18.0  # μm
    total_height = 3.0  # μm
    
    # Wave parameters
    num_points = 500  # smooth curves
    num_periods = 3.0  # number of complete oscillations
    amplitude = 0.45  # amplitude of sine wave (increased)
    
    # Waveguide parameters
    wg_width = 0.7  # width of each band (increased)
    separation = 0.9  # vertical separation between centerlines
    
    # Create x coordinates
    x = np.linspace(0, length, num_points)
    
    # Create sinusoidal modulation for top waveguide
    y_modulation_top = amplitude * np.sin(2 * np.pi * num_periods * x / length)
    
    # Create sinusoidal modulation for bottom waveguide (180° phase shift)
    y_modulation_bottom = -amplitude * np.sin(2 * np.pi * num_periods * x / length)
    
    # Top waveguide path
    y_top = total_height/2 + separation/2 + y_modulation_top
    points_top = np.column_stack([x, y_top])
    path_top = gf.Path(points_top)
    
    # Bottom waveguide path (with opposite phase modulation)
    y_bottom = total_height/2 - separation/2 + y_modulation_bottom
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