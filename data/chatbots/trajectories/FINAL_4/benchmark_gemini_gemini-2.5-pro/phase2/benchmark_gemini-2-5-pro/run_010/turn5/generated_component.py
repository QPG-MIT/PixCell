import gdsfactory as gf
import numpy as np

@gf.cell
def create_component():
    """
    Creates a wavy directional coupler component.

    This component consists of two sinusoidal waveguides that are vertically
    mirrored, matching the target image and fitting within the 18x3 um footprint.

    Parameter Derivation:
    - Let H=3.0 be total height, w=width, A=amplitude, d=centerline separation,
      and g=minimum gap.
    - H = d + 2*A + w
    - g = d - 2*A - w
    - By visual estimation, we assume w ≈ g. Let's set w = g = 0.7 um.
    - Solving the system of equations:
        1) 3.0 = d + 2*A + 0.7  =>  d + 2*A = 2.3
        2) 0.7 = d - 2*A - 0.7  =>  d - 2*A = 1.4
    - This gives: d = 1.85 um and A = 0.225 um.
    """
    # Create the parent component to hold both waveguides
    c = gf.Component()

    # 1. Define device parameters based on the new analysis
    length = 18.0
    waveguide_width = 0.7
    amplitude = 0.225
    centerline_separation = 1.85  # This is 'd'
    num_points = 201

    # 2. Create the path for the top waveguide
    # The centerline is y = (d/2) + A*cos(x)
    x_coords = np.linspace(-length / 2, length / 2, num_points)
    y_coords_top = (centerline_separation / 2) + amplitude * np.cos(
        2 * np.pi * x_coords / length
    )
    points_top = list(zip(x_coords, y_coords_top))
    path_top = gf.Path(points_top)

    # 3. Create the path for the bottom waveguide
    # The centerline is y = -(d/2) - A*cos(x)
    y_coords_bottom = (-centerline_separation / 2) - amplitude * np.cos(
        2 * np.pi * x_coords / length
    )
    points_bottom = list(zip(x_coords, y_coords_bottom))
    path_bottom = gf.Path(points_bottom)

    # 4. Define the cross-section and extrude both paths into components
    xs = gf.cross_section.cross_section(width=waveguide_width)
    wg_top = gf.path.extrude(path_top, cross_section=xs)
    wg_bottom = gf.path.extrude(path_bottom, cross_section=xs)

    # 5. Add the two waveguide components as references to the parent cell
    c.add_ref(wg_top)
    c.add_ref(wg_bottom)

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