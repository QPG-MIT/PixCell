import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_coupler():
    """
    Creates a device with two parallel, wavy waveguides that are mirror
    images of each other, matching the target image.
    The waveguides have a constant width, and their centerlines follow a
    cosine curve.
    """
    # 1. Define device parameters based on footprint and visual analysis.
    length = 18.0
    width = 0.5

    # These parameters are derived to match the footprint height (3um)
    # and to create a visually plausible gap variation (min gap = 0.5um).
    # A = amplitude of the cosine wave's centerline.
    # D = vertical offset of the centerline from the x-axis.
    amplitude = 0.375
    centerline_offset = 0.875  # This is D

    num_points = 201  # Number of points to define the curve for smoothness.

    # 2. Define the upper wavy waveguide as a standalone component.
    # We will instance this component twice (once normal, once mirrored).
    
    # Generate the points for the top waveguide's centerline path.
    # The path follows a cosine function to have the widest gap at the ends.
    x_coords = np.linspace(0, length, num_points)
    y_coords = centerline_offset + amplitude * np.cos(2 * np.pi * x_coords / length)
    points = list(zip(x_coords, y_coords))

    # Create the path object from the generated points.
    path = gf.Path(points)

    # **FIX:** Define a cross_section and pass it to extrude().
    # The extrude function requires a cross_section object, not just a width.
    xs = gf.cross_section.cross_section(width=width)
    wg_single_wavy = gf.path.extrude(path, cross_section=xs)


    # 3. Assemble the two waveguides into the final component.
    c = gf.Component("wavy_coupler_device")

    # Add the top waveguide as a reference.
    ref_top = c << wg_single_wavy

    # Add the bottom waveguide by referencing the same component and mirroring it.
    ref_bottom = c << wg_single_wavy
    ref_bottom.mirror(p1=(0, 0), p2=(1, 0))  # Mirror across the x-axis.

    # Center the whole device at (0, 0).
    c.movex(-length / 2)

    # 4. Expose the ports for external connections.
    c.add_port("o1", port=ref_top.ports["o1"])
    c.add_port("o2", port=ref_top.ports["o2"])
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