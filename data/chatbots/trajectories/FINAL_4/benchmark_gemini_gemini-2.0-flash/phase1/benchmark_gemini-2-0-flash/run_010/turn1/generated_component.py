import gdsfactory as gf
from gdsfactory.component import Component
import numpy as np  # Import numpy

@gf.cell
def wavy_lines() -> Component:
    """Creates two wavy lines using GDSFactory parametric functions."""
    
    c = gf.Component("wavy_lines")

    # Parameters for the wavy lines
    waveguide_width = 1.0
    amplitude = 0.5
    period = 8.0
    length = 18.0  # Match the footprint x-dimension
    y_offset = 2.0 # Gap between lines 

    # Create a path for a single wavy line
    points = []
    for x in range(int(length*10)):
        x_val = x/10.0
        y_val = amplitude * np.sin(2 * np.pi * x_val / period) # Use np.sin
        points.append((x_val, y_val))

    path = gf.Path(points=points)

    # Extrude the path to create the first wavy waveguide
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))
    wavy_wg1 = path.extrude(cross_section=xs)
    wavy_ref1 = c << wavy_wg1

    # Create the second wavy waveguide by translating the first
    wavy_ref2 = c << wavy_wg1
    wavy_ref2.movey(y_offset)

    # Add ports to the beginning and end of the first line
    c.add_port(name="o1", port=wavy_ref1.ports["o1"])
    c.add_port(name="o2", port=wavy_ref1.ports["o2"])
    return c


if __name__ == "__main__":
    c = wavy_lines()
    c.show(show_ports=True)