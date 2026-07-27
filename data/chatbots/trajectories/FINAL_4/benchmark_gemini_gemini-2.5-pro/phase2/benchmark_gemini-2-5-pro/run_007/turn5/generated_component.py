import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_coupler():
    """
    Creates a device with two parallel, wavy waveguides that are mirror
    images of each other, matching the target image.

    The key feature is that the gap between the waveguides is narrowest in
    the middle and widest at the ends. This is achieved by using a positive
    cosine function for the waveguide path.
    """
    # 1. Define device parameters based on footprint and visual analysis.
    length = 18.0
    width = 0.5

    # These parameters are derived to match the footprint height (3um)
    # and to create the desired gap variation.
    # A = amplitude of the cosine wave's centerline.
    # D = vertical offset of the centerline from the x-axis.
    amplitude = 0.375
    centerline_offset = 0.875

    num_points = 201  # Number of points to define the curve for smoothness.

    # 2. Define a single wavy waveguide shape. This will be instanced twice.

    # Generate the points for the centerline path.
    # The path follows a POSITIVE cosine function. This creates a shape that
    # starts high, dips in the middle, and ends high. This will be our TOP
    # waveguide.
    # Mirroring this shape across the x-axis creates a shape that starts
    # low, humps up in the middle, and ends low (our BOTTOM waveguide).
    # This combination results in the widest gap at the ends and the
    # narrowest gap in the middle, matching the target image.
    x_coords = np.linspace(0, length, num_points)

    # --- FIX ---
    # The sign of the amplitude term is flipped from '-' to '+' compared to the
    # previous version. This inverts the phase of the wave.
    # Old: D - A*cos(...) -> narrowest gap at ends, widest in middle.
    # New: D + A*cos(...) -> widest gap at ends, narrowest in middle.
    y_coords = centerline_offset + amplitude * np.cos(2 * np.pi * x_coords / length)
    # --- END FIX ---

    points = list(zip(x_coords, y_coords))

    # Create the path object from the generated points.
    path = gf.Path(points)

    # Define the cross_section and extrude the path to create the waveguide component.
    xs = gf.cross_section.cross_section(width=width)
    wg_base_shape = gf.path.extrude(path, cross_section=xs)


    # 3. Assemble the two waveguides into the final component.
    c = gf.Component("wavy_coupler_device")

    # The base shape is the "dip down" curve, which is our top waveguide.
    ref_top = c << wg_base_shape

    # The bottom waveguide is created by mirroring the base shape across the x-axis.
    # This creates the "hump up" curve.
    ref_bottom = c << wg_base_shape
    ref_bottom.mirror(p1=(0, 0), p2=(1, 0))

    # Center the whole device at (0, 0) for conventional placement.
    c.movex(-length / 2)

    # 4. Expose the ports for external connections, ensuring correct naming.
    # Ports o1 and o2 belong to the top waveguide (the original instance).
    c.add_port("o1", port=ref_top.ports["o1"])
    c.add_port("o2", port=ref_top.ports["o2"])

    # Ports o3 and o4 belong to the bottom waveguide (the mirrored instance).
    c.add_port("o3", port=ref_bottom.ports["o1"])
    c.add_port("o4", port=ref_bottom.ports["o2"])

    return c

# Main script execution block to generate the GDS file.
if __name__ == "__main__":
    # Instantiate the component.
    recreated_device = wavy_coupler()

    # Write the component to a GDSII file.
    recreated_device.write_gds("wavy_coupler.gds")

    # The following line can be uncommented to display the layout visually.
    # recreated_device.show()
    # print("GDS file 'wavy_coupler.gds' has been generated.")