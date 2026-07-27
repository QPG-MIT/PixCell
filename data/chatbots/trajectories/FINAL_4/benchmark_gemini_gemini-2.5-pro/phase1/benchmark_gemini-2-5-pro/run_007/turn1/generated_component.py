import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_channel_coupler():
    """
    Creates a device with two parallel wavy waveguides, resembling a cosine curve.

    The geometry is derived from the provided image and footprint [18, 3] um.
    """
    # 1. Define device parameters derived from the footprint and image proportions.
    # Total footprint dimensions
    device_length = 18.0
    device_height = 3.0

    # From visual analysis and solving a system of equations based on proportions:
    # w = waveguide_width
    # A = amplitude of the cosine wave's centerline
    # y_offset = vertical offset of each waveguide's centerline from y=0
    #
    # Equations derived:
    # 1) Total Height: 2 * (y_offset + A + w/2) = 3.0
    # 2) Proportions (end_gap = w): w = 2 * (y_offset + A - w/2)
    # 3) Proportions (mid_gap = w/2): w/2 = 2 * (y_offset - A - w/2)
    #
    # Solving this system yields:
    waveguide_width = 1.0
    amplitude = 0.125
    centerline_offset = 0.875

    # 2. Generate the points for the base path (a single cosine period).
    # We create a path centered at y=0, which we will later move.
    num_points = 201  # A higher number of points for a smooth curve.
    x_coords = np.linspace(0, device_length, num_points)
    # y = A * cos(2*pi*x/L) -> starts high, dips in the middle, ends high.
    y_coords = amplitude * np.cos(2 * np.pi * x_coords / device_length)
    points = np.array([x_coords, y_coords]).T

    # 3. Create a GDSFactory Path object from the generated points.
    cosine_path = gf.Path(points)

    # 4. Extrude the path with a constant width to create a single wavy waveguide.
    # We use a simple cross_section with the calculated width.
    xs = gf.cross_section.cross_section(width=waveguide_width)
    single_wavy_wg = gf.path.extrude(cosine_path, cross_section=xs)

    # 5. Assemble the final component by placing two instances of the wavy waveguide.
    c = gf.Component("wavy_channel_coupler")

    # Add the top waveguide and move it to its final vertical position.
    top_wg = c << single_wavy_wg
    top_wg.movey(centerline_offset)

    # Add the bottom waveguide, mirror it across the x-axis, and move it down.
    bottom_wg = c << single_wavy_wg
    bottom_wg.mirror(p1=(0, 0), p2=(1, 0))  # Mirrors across the horizontal axis
    bottom_wg.movey(-centerline_offset)

    # Center the entire component at (0, 0) for good practice.
    c.movex(-device_length / 2)

    return c

# Main script execution block
if __name__ == "__main__":
    # Instantiate the component.
    recreated_device = wavy_channel_coupler()

    # CORRECTED LINE: Added the command to write the component to a GDS file.
    # This will create 'wavy_channel_coupler.gds' in the same directory.
    recreated_device.write_gds("wavy_channel_coupler.gds")

    # You can still use .show() for visual verification during development.
    # recreated_device.show()
    # print(f"Component size: {recreated_device.size}")
    # print(f"Expected footprint: [18.0, 3.0]")
    # print("GDS file 'wavy_channel_coupler.gds' has been generated.")