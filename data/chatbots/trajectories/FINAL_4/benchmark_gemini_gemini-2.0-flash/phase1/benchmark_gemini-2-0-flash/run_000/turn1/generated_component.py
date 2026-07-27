import gdsfactory as gf
import numpy as np  # Import numpy explicitly

@gf.cell
def wavy_device():
    c = gf.Component("wavy_device")

    # Define parameters
    waveguide_width = 1  # Adjust based on image
    spacing = 1  # Adjust based on image
    amplitude = 1  # Adjust based on image
    wavelength = 16  # Adjust based on image

    # Create a straight path
    p = gf.Path()
    p.append(gf.path.straight(length=wavelength))

    # Create a sine wave modulation
    def sine_wave(t):
        return (t, amplitude * np.sin(2 * np.pi * t / wavelength))

    # Apply sine wave deformation to path
    p.points = [sine_wave(t) for t in np.linspace(0, wavelength, 100)]  # Adjust density as needed
    # Corrected list comprehension
    new_points = []
    for point in p.points:
        new_points.append([point[0], point[1]])
    p.points = new_points

    # Extrude the path for the top waveguide
    xs = gf.cross_section.strip(width=waveguide_width, layer=(1, 0))
    top_waveguide = c << gf.path.extrude(p, cross_section=xs)

    # Translate the path for the bottom waveguide
    p_bottom = gf.Path(points=p.points)
    p_bottom.move((0, -waveguide_width - spacing - 2*amplitude))

    # Extrude the translated path for the bottom waveguide
    bottom_waveguide = c << gf.path.extrude(p_bottom, cross_section=xs)

    # Add ports
    c.add_port(name="o1", port=top_waveguide.ports["o1"])
    c.add_port(name="o2", port=top_waveguide.ports["o2"])
    c.add_port(name="o3", port=bottom_waveguide.ports["o1"])
    c.add_port(name="o4", port=bottom_waveguide.ports["o2"])

    return c

# Example usage
device = wavy_device()
device.show(show_ports=True)