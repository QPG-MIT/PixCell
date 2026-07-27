import gdsfactory as gf
import numpy as np

@gf.cell
def create_component():
    """
    Creates the sinusoidal waveguide pair based on the provided image and footprint.

    The geometry is derived by deconstructing the footprint (18um x 3um) and
    the visual proportions of the image. The device consists of two identical
    sinusoidal waveguides, where one is a vertical mirror of the other.

    Derived Parameters:
    - Total length (L): 18.0 um
    - Total height (H): 3.0 um
    - Assuming relations from visual inspection:
      - Waveguide width (w)
      - Wave amplitude (A)
      - Center-to-center vertical separation (d_y)
      - Peak-to-peak amplitude of a single wave equals its width: 2*A = w
      - The central gap between the waveguides equals the width: d_y - w = w => d_y = 2*w
    - The total height is H = d_y + 2*A + w.
    - Substituting the relations: 3.0 = (2*w) + w + w = 4*w.
    - Solving for the parameters:
      - w = 0.75 um
      - A = w / 2 = 0.375 um
      - d_y = 2 * w = 1.5 um
    """
    # 1. Define device parameters from the derivation
    length = 18.0
    waveguide_width = 0.75
    amplitude = 0.375
    center_separation = 1.5
    num_points = 201  # Resolution for the sine curve

    # 2. Create a single sinusoidal waveguide using a parametric path.
    # Generating points from a mathematical formula is a parametric approach that
    # avoids hardcoding vertices.
    x_coords = np.linspace(0, length, num_points)
    y_coords = amplitude * np.sin(2 * np.pi * x_coords / length)
    points = list(zip(x_coords, y_coords))
    
    path = gf.Path(points)
    xs = gf.cross_section.cross_section(width=waveguide_width)
    single_wave_component = gf.path.extrude(path, cross_section=xs)

    # 3. Assemble the final device in a new component
    c = gf.Component("dual_sinusoidal_waveguide")

    # Add the top waveguide
    top_wave = c << single_wave_component
    
    # Add the bottom waveguide by mirroring the original component
    bottom_wave = c << single_wave_component
    bottom_wave.mirror()

    # 4. Position the waveguides vertically and center the component
    # The whole component should be centered at (0,0) for good practice
    top_wave.movey(center_separation / 2)
    bottom_wave.movey(-center_separation / 2)
    c.movex(-length / 2)

    return c

# Fix: The original script defined the component factory function but never
# called it to create an instance of the component or write it to a file.
# The following lines instantiate the component and save it to a GDS file.
if __name__ == "__main__":
    # Create an instance of the component
    component_to_save = create_component()
    
    # Write the component to a GDS file
    component_to_save.write_gds("output.gds")

    # Optional: show the component in a viewer if available
    component_to_save.show()