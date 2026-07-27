import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_ribbon():
    """
    Creates a component with two wavy ribbons as shown in the image.
    """
    c = gf.Component("wavy_ribbon")

    # Define cross-section for the ribbons
    xs = gf.cross_section.cross_section(width=1, layer=(1, 0))  # Adjust width to match image

    # Parameters for the sine wave
    amplitude = 0.5  # Adjust to match image
    period = 9  # Adjust to match image
    num_periods = 2

    # Create a path using gdsfactory's Path function
    p = gf.Path()

    # Initial position
    x0, y0 = 0, 0

    # Generate the points for the sine wave path
    points = [(x0, y0)]
    for i in range(1, 100*num_periods):
        x = i * (period / 100)
        y = amplitude * np.sin(2 * np.pi * x / period)
        points.append((x, y))

    p.points = points

    # Create upper waveguide by extruding the path
    upper_wg = c << p.extrude(cross_section=xs)
    upper_wg.name = "upper_waveguide"
    # Access ports correctly by name
    c.add_port("o1", port=upper_wg.ports["o1"])
    c.add_port("o2", port=upper_wg.ports["o2"])

    # Create lower waveguide by mirroring and translating the upper waveguide
    lower_wg = c << p.extrude(cross_section=xs)
    lower_wg.name = "lower_waveguide"
    lower_wg.mirror()
    lower_wg.movey(-2.0*amplitude) # Move down vertically
    # Access ports correctly by name
    c.add_port("o3", port=lower_wg.ports["o1"])
    c.add_port("o4", port=lower_wg.ports["o2"])

    # Adjust the y translation based on image, the gap between the lines.
    lower_wg.movey(-1)

    # Rotate to match image
    c.rotate(180)

    return c

# Create and save the component
wavy = wavy_ribbon()
wavy.show(show_ports=True)