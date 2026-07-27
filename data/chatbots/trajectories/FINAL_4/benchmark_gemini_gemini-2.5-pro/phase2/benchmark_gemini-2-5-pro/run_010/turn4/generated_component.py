import gdsfactory as gf
import numpy as np

@gf.cell
def create_component():
    """
    Creates a single sinusoidal waveguide component.

    The geometry consists of a single waveguide following a sinusoidal path,
    designed to match the target image and fit within the specified
    18x3 um footprint.

    Parameter Derivation:
    - Footprint: Length L=18um, Height H=3um.
    - The target image shows a 'trough-peak-trough' shape, which corresponds
      to a positive cosine function over one period.
    - Let w = waveguide_width and A = amplitude.
    - The total height of the component is H_comp = 2*A + w.
    - To maximize the use of the 3um vertical footprint, we set H_comp = 3.0um.
    - Visually estimating the waveguide width 'w' to be ~0.75um.
    - Solving for amplitude: 3.0 = 2*A + 0.75 => 2*A = 2.25 => A = 1.125um.
    """
    # 1. Define device parameters based on the new analysis
    length = 18.0
    waveguide_width = 0.75
    amplitude = 1.125
    num_points = 201

    # 2. Create the sinusoidal path, centered at the origin (x=0).
    # A positive cosine function generates the required 'trough-peak-trough' shape
    # when plotted over a full period from -L/2 to L/2.
    x_coords = np.linspace(-length / 2, length / 2, num_points)
    y_coords = amplitude * np.cos(2 * np.pi * x_coords / length)
    points = list(zip(x_coords, y_coords))

    path = gf.Path(points)

    # 3. Extrude the path to create the final waveguide component.
    # The component is implicitly centered at (0,0) due to the path definition.
    xs = gf.cross_section.cross_section(width=waveguide_width)
    c = gf.path.extrude(path, cross_section=xs)

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