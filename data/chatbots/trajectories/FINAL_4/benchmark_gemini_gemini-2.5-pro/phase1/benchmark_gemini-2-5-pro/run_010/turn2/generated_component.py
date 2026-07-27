import gdsfactory as gf
import numpy as np

@gf.cell
def create_component():
    """
    Creates a single sinusoidal waveguide based on the provided image.

    The geometry is a single sinusoidal waveguide, which corresponds to the
    bottom half of the previously generated dual-waveguide component. The
    parameters for the wave's shape are kept the same. The wave starts
    by going downwards, which is achieved by mirroring a standard sine
    wave path across the horizontal axis.

    Derived Parameters (from previous component analysis):
    - Total length (L): 18.0 um
    - Waveguide width (w): 0.75 um
    - Wave amplitude (A): 0.375 um
    """
    # 1. Define device parameters
    length = 18.0
    waveguide_width = 0.75
    amplitude = 0.375
    num_points = 201  # Resolution for the sine curve

    # 2. Create a base sinusoidal component using a parametric path.
    # The path is generated from a sine function, which starts at y=0 and goes up.
    x_coords = np.linspace(0, length, num_points)
    y_coords = amplitude * np.sin(2 * np.pi * x_coords / length)
    points = list(zip(x_coords, y_coords))
    
    path = gf.Path(points)
    xs = gf.cross_section.cross_section(width=waveguide_width)
    base_wave_component = gf.path.extrude(path, cross_section=xs)

    # 3. Assemble the final device in a new component
    c = gf.Component("single_sinusoidal_waveguide")

    # Add the base wave as a reference
    wave = c << base_wave_component
    
    # The target image shows the wave starting by going down. Our base wave
    # starts by going up. We achieve the desired shape by mirroring the base
    # component across the x-axis.
    wave.mirror()

    # 4. Center the component horizontally at the origin for good practice.
    # It is already centered vertically after the mirror operation.
    c.movex(-length / 2)

    return c

# The main execution block calls the factory function and writes the
# resulting component to a GDS file.
if __name__ == "__main__":
    # Create an instance of the component
    component_to_save = create_component()
    
    # Write the component to a GDS file
    component_to_save.write_gds("output.gds")

    # Optional: show the component in a viewer if available
    component_to_save.show()