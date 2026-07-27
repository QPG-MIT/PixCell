import gdsfactory as gf
import numpy as np

@gf.cell
def create_wavy_coupler():
    """
    Creates a wavy directional coupler using the Path and extrude method.

    This approach models the device as two constant-width waveguides
    following sinusoidal paths, which accurately matches the target image.
    The previous polygon-based method was incorrect as it created shapes
    of variable width.
    """
    c = gf.Component("wavy_coupler")

    # --- Parameters derived from footprint [18, 3] and image analysis ---
    length = 18.0
    waveguide_width = 1.0
    n_points = 201

    # --- Define the path for the top waveguide's centerline ---
    # The path is modeled as y(x) = A * cos(2*pi*x/L) + C
    # We solve for amplitude (A) and vertical offset (C) based on the
    # desired gap at the center and ends, and the total device height.

    # From image analysis:
    # Desired gap at ends: ~1.0 um
    # Desired gap at center: ~0.2 um
    # Total height at ends: 3.0 um (from footprint)
    # Waveguide width is assumed to be 1.0 um.

    # The gap between the two waveguides is: gap(x) = 2*y_centerline(x) - waveguide_width
    # From this, we can find the required centerline y-position at ends and center:
    # 1.0 = 2 * y_centerline(x=0) - 1.0  => y_centerline(x=0) = 1.0
    # 0.2 = 2 * y_centerline(x=L/2) - 1.0 => y_centerline(x=L/2) = 0.6

    # Now solve for A and C using the centerline equation y(x) = A*cos(2*pi*x/L) + C:
    # y(0)   = A * cos(0) + C = A + C = 1.0
    # y(L/2) = A * cos(pi) + C = -A + C = 0.6
    #
    # Solving this system of equations:
    # (A + C) + (-A + C) = 1.0 + 0.6  =>  2C = 1.6 => C = 0.8 (vertical_offset)
    # Substitute C into first eq: A + 0.8 = 1.0 => A = 0.2 (amplitude)

    amplitude = 0.2
    vertical_offset = 0.8

    # Generate the points for the path
    x_coords = np.linspace(0, length, n_points)
    y_coords = amplitude * np.cos(2 * np.pi * x_coords / length) + vertical_offset

    points = list(zip(x_coords, y_coords))

    # --- Create the waveguide from the path ---
    # Define the constant-width cross-section
    xs = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))

    # Create the path object
    p = gf.Path(points)

    # Extrude the path to create a single wavy waveguide component
    waveguide_top = gf.path.extrude(p, cross_section=xs)

    # --- Assemble the final coupler component ---
    # Add the top waveguide as a reference
    wg_top_ref = c << waveguide_top
    
    # Add a mirrored version for the bottom waveguide
    wg_bottom_ref = c << waveguide_top
    wg_bottom_ref.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across the x-axis

    # Add ports to the main component, referencing the sub-component ports.
    # The port order convention is o1, o2 on the left (top to bottom)
    # and o3, o4 on the right (bottom to top).
    c.add_port("o1", port=wg_top_ref.ports["o1"])
    c.add_port("o2", port=wg_bottom_ref.ports["o1"])
    c.add_port("o3", port=wg_bottom_ref.ports["o2"])
    c.add_port("o4", port=wg_top_ref.ports["o2"])

    return c

# Main execution block for testing and saving
if __name__ == "__main__":
    wavy_coupler_device = create_wavy_coupler()
    wavy_coupler_device.show()
    wavy_coupler_device.write_gds("wavy_coupler.gds")
    print("Successfully created and saved wavy_coupler.gds using path extrusion.")