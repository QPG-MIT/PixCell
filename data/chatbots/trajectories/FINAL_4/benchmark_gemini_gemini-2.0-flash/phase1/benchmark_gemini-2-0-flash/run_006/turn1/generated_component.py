import gdsfactory as gf
import numpy as np

@gf.cell
def double_waveguide():
    c = gf.Component("double_waveguide")
    
    # Define waveguide parameters
    wg_width = 1  # Estimate from image
    wg_amplitude = 0.5 # Estimate from image
    wg_period = 9  # Estimate from image
    wg_length = 18  # From footprint constraint
    num_points = 100 # Number of points to define the curve

    # Create the top waveguide
    points_top = []
    for i in range(num_points):
        t = i / (num_points - 1)
        x = t * wg_length
        y = wg_amplitude * np.sin(2 * np.pi * x / wg_period) + 1  # Offset to be at top
        points_top.append((x, y))

    path_top = gf.Path(points_top)
    wg_top = c << path_top.extrude(width=wg_width, layer=(1, 0))

    # Create the bottom waveguide
    points_bottom = []
    for i in range(num_points):
        t = i / (num_points - 1)
        x = t * wg_length
        y = wg_amplitude * np.sin(2 * np.pi * x / wg_period) - 1  # Offset to be at bottom
        points_bottom.append((x, y))

    path_bottom = gf.Path(points_bottom)
    wg_bottom = c << path_bottom.extrude(width=wg_width, layer=(1, 0))

    # Add ports
    c.add_port(name="o1", port=wg_top.ports["o1"])
    c.add_port(name="o2", port=wg_top.ports["o2"])
    c.add_port(name="o3", port=wg_bottom.ports["o1"])
    c.add_port(name="o4", port=wg_bottom.ports["o2"])

    return c

if __name__ == "__main__":
    c = double_waveguide()
    c.show(show_ports=True)