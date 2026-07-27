import gdsfactory as gf
import numpy as np

@gf.cell
def create_component():
    """
    Creates a dual anti-phase sinusoidal waveguide coupler.

    The geometry consists of two parallel sinusoidal waveguides that are
    out of phase by 180 degrees. The parameters are derived to match the
    target image and fit within the specified 18x3 um footprint.

    Parameter Derivation:
    - Footprint: Length L=18um, Height H=3um.
    - Let w = waveguide_width, A = amplitude, g = gap, y_off = vertical
      offset of each waveguide centerline from y=0.
    - Visually, the gap 'g' is approximately equal to the width 'w'.
    - Total height H = 2*y_off + 2*A + w.
    - Narrowest gap g = 2*y_off - 2*A - w.
    - Assuming g=w and estimating w=0.75um, we solve the system:
      - 3.0 = 2*y_off + 2*A + 0.75
      - 0.75 = 2*y_off - 2*A - 0.75
    - This yields amplitude A = 0.1875 um and centerline offset
      y_off = 0.9375 um.
    """
    # 1. Define derived device parameters
    length = 18.0
    waveguide_width = 0.75
    amplitude = 0.1875
    vertical_offset = 0.9375  # y-offset for each waveguide's centerline
    num_points = 201  # Resolution for the curve

    # 2. Create a base component using a cosine-based parametric path.
    # A cosine shape (peak, trough, peak) matches the top waveguide natively.
    x_coords = np.linspace(0, length, num_points)
    y_coords = amplitude * np.cos(2 * np.pi * x_coords / length)
    points = list(zip(x_coords, y_coords))

    path = gf.Path(points)
    xs = gf.cross_section.cross_section(width=waveguide_width)
    base_wave_component = gf.path.extrude(path, cross_section=xs)

    # 3. Assemble the final device in a new component
    c = gf.Component("dual_sinusoidal_waveguide")

    # Create and position the top waveguide.
    # It already has the correct cosine shape, just needs to be moved up.
    wave_top = c << base_wave_component
    wave_top.movey(vertical_offset)

    # Create and position the bottom waveguide.
    # It needs to be a mirrored (anti-phase) version of the top one.
    wave_bottom = c << base_wave_component
    wave_bottom.mirror()  # Mirror across x-axis to get the -cos shape
    wave_bottom.movey(-vertical_offset)

    # 4. Center the component horizontally at the origin for good practice.
    # It is already centered vertically by the symmetric offset design.
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