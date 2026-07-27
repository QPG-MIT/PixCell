import gdsfactory as gf
import numpy as np

@gf.cell
def improved_sinusoidal_waveguide_pair():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a smooth sinusoidal path for the top waveguide
    # Generate points for a smooth sine wave from x=0 to x=18
    x_points = np.linspace(0, 18, 100)  # More points for smoother curve
    # Create a sine wave that goes from y=1.5 to y=0.5 and back to y=1.5
    # This creates the S-bend shape
    y_points = 1.0 + 0.5 * np.cos(np.pi * x_points / 18)  # Smooth transition
    
    top_points = [(x, y) for x, y in zip(x_points, y_points)]
    top_path = gf.path.smooth(points=top_points, radius=2.0)
    top_waveguide = gf.path.extrude(top_path, cross_section=xs)
    
    # Create the path for the bottom waveguide (mirrored)
    # Mirror the y-coordinates to create perfect symmetry
    bottom_points = [(x, -y) for x, y in zip(x_points, y_points)]
    bottom_path = gf.path.smooth(points=bottom_points, radius=2.0)
    bottom_waveguide = gf.path.extrude(bottom_path, cross_section=xs)
    
    # Add both waveguides to the component
    top_ref = c << top_waveguide
    bottom_ref = c << bottom_waveguide
    
    # Add ports for connectivity
    c.add_port("o1_top", port=top_ref.ports["o1"])
    c.add_port("o2_top", port=top_ref.ports["o2"])
    c.add_port("o1_bottom", port=bottom_ref.ports["o1"])
    c.add_port("o2_bottom", port=bottom_ref.ports["o2"])
    
    return c

# Create and save the device
device = improved_sinusoidal_waveguide_pair()
device.write_gds("improved_sinusoidal_waveguide_pair.gds")