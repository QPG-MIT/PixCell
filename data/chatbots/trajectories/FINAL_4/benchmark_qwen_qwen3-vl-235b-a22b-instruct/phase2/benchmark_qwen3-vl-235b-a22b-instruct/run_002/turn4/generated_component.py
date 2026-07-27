import gdsfactory as gf
import numpy as np

@gf.cell
def improved_diverging_waveguide_pair():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a straight path for the top waveguide that gradually moves upward
    # Generate points for a straight line from x=0 to x=18
    x_points = np.linspace(0, 18, 100)
    # Create a linear divergence: y increases from 0 to 1.5 as x goes from 0 to 18
    y_points_top = 0.75 + 0.75 * (x_points / 18)  # Starts at y=0.75, ends at y=1.5
    
    top_points = [(x, y) for x, y in zip(x_points, y_points_top)]
    top_path = gf.path.smooth(points=top_points, radius=2.0)
    top_waveguide = gf.path.extrude(top_path, cross_section=xs)
    
    # Create the path for the bottom waveguide (symmetric divergence)
    # y decreases from 0 to -1.5 as x goes from 0 to 18
    y_points_bottom = 0.75 - 0.75 * (x_points / 18)  # Starts at y=0.75, ends at y=0
    
    bottom_points = [(x, y) for x, y in zip(x_points, y_points_bottom)]
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
device = improved_diverging_waveguide_pair()
device.write_gds("improved_diverging_waveguide_pair.gds")