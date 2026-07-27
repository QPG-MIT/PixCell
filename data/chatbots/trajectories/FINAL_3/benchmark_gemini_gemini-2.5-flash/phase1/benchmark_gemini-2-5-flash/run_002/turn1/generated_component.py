import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec

@gf.cell
def custom_coupler(
    width: float = 0.5,
    gap_inner: float = 0.2, # Gap between the inner edges of the two waveguides in the central coupling region
    length_io: float = 20.0, # Length of the straight input/output sections
    length_coupling: float = 40.0, # Length of the straight parallel section in the middle
    length_bend_x: float = 20.0, # X-projection length of each individual bend section
    bend_radius: float = 10.0, # Minimum bend radius for the smooth Euler bends
    cross_section: CrossSectionSpec = "strip",
) -> gf.Component:
    """
    Creates a custom 2x2 coupler geometry with two parallel S-bent waveguides,
    matching the provided image and footprint.

    The device consists of two waveguides that start parallel, converge with a smooth
    bend, run parallel in a coupling region, diverge with another smooth bend, and
    finish parallel.

    Args:
        width: Width of the waveguides. Defaults to 0.5 µm.
        gap_inner: Gap between the inner edges of the two waveguides in the central
                   coupling region. Defaults to 0.2 µm.
        length_io: Length of the straight input and output sections. Defaults to 20 µm.
        length_coupling: Length of the straight parallel section in the middle.
                         Defaults to 40 µm.
        length_bend_x: The horizontal (x-axis) projection length of each of the two
                       bend sections. Defaults to 20 µm.
        bend_radius: The minimum bend radius used by `gf.path.smooth` for the
                     Euler bends. Defaults to 10 µm.
        cross_section: Specification for the waveguide cross-section. Defaults to
                       "strip" (a basic rectangular cross-section).

    Returns:
        A GDSFactory component representing the custom coupler.
    """
    c = gf.Component("custom_coupler")
    xs = gf.get_cross_section(cross_section, width=width)

    # The total device footprint is [120, 4] µm.
    # We'll center the device vertically at y=0.
    # This means the top edge of the top waveguide is at y=2 µm, and the bottom
    # edge of the bottom waveguide is at y=-2 µm.

    # Calculate the y-coordinate for the centerline of the top waveguide
    # at the input/output sections (outer separation).
    # Its top edge is at y=2, so its centerline is at y = 2 - (width / 2).
    y_top_outer_cl = 2 - (width / 2)

    # Calculate the y-coordinate for the centerline of the top waveguide
    # in the central coupling region (inner separation).
    # The gap between inner edges is `gap_inner`.
    # The distance from y=0 to the centerline of the top waveguide is
    # (gap_inner / 2) + (width / 2).
    y_top_inner_cl = (gap_inner / 2) + (width / 2)

    # Define the control points for the centerline of the top waveguide.
    # These points define the straight sections and the start/end points of the bends.
    # The x-coordinates sum up to the total device length (120 µm).
    P_top_centerline = [
        (0, y_top_outer_cl),  # Start of input straight
        (length_io, y_top_outer_cl),  # End of input straight, start of first bend
        (length_io + length_bend_x, y_top_inner_cl),  # End of first bend, start of coupling straight
        (length_io + length_bend_x + length_coupling, y_top_inner_cl),  # End of coupling straight, start of second bend
        (length_io + 2 * length_bend_x + length_coupling, y_top_outer_cl),  # End of second bend, start of output straight
        (length_io + 2 * length_bend_x + length_coupling + length_io, y_top_outer_cl),  # End of output straight
    ]

    # Calculate the total x-length to verify against the footprint constraint.
    total_x_length = P_top_centerline[-1][0]
    if abs(total_x_length - 120.0) > 1e-9:
        raise ValueError(f"Calculated x-length ({total_x_length:.2f} µm) does not match "
                         f"footprint x-dimension (120 µm). Adjust length_io, length_coupling, "
                         f"or length_bend_x. Current sum: {2*length_io + 2*length_bend_x + length_coupling}")

    # Create the path for the top waveguide using smooth bends between control points.
    # The `gf.path.smooth` function typically defaults to Euler bends when a `radius`
    # is provided, which gives the desired smooth, adiabatic transitions.
    # Explicitly setting `bend_type` or `bend_factory` to `gf.path.euler` was causing
    # a TypeError because `smooth` was attempting to pass that argument directly
    # to the `euler` function it uses internally, which doesn't expect it.
    path_top_obj = gf.path.smooth(
        points=P_top_centerline,
        radius=bend_radius,
    )

    # Extrude the path with the defined cross-section to create the GDS geometry.
    wg_top = c << gf.path.extrude(path_top_obj, cross_section=xs)

    # Create the bottom waveguide by mirroring the top one across the x-axis (y=0).
    wg_bottom = c << gf.path.extrude(path_top_obj, cross_section=xs)
    wg_bottom.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across the horizontal axis

    # Add ports to the component for external connection.
    # Standard naming convention for a 2x2 device:
    # o1: top-left, o2: bottom-left, o3: top-right, o4: bottom-right
    c.add_port("o1", port=wg_top.ports["o1"])
    c.add_port("o2", port=wg_bottom.ports["o1"])
    c.add_port("o3", port=wg_top.ports["o2"])
    c.add_port("o4", port=wg_bottom.ports["o2"])

    # Verify the total y-height of the component.
    # The total vertical span from the top edge of the top waveguide to the bottom
    # edge of the bottom waveguide should be 4 µm.
    # Max Y: y_top_outer_cl + width / 2 = (2 - width/2) + width/2 = 2
    # Min Y: -(y_top_outer_cl + width / 2) = -2
    # Total Y span = 2 - (-2) = 4
    if abs(c.ysize - 4.0) > 1e-9:
        raise ValueError(f"Calculated y-size ({c.ysize:.2f} µm) does not match "
                         f"footprint y-dimension (4 µm). Check width or vertical positioning logic.")

    return c

# Example usage and verification:
if __name__ == "__main__":
    # Create the component with default parameters
    device = custom_coupler()
    print(f"Component name: {device.name}")
    print(f"Component ports: {device.ports}")

    # Verify the footprint of the created device.
    # The @gf.cell decorator by default places the component such that its
    # bounding box starts at (0,0) or is centered if no ports constrain it.
    # In this case, our path definition already spans [0, 120] in x and [-2, 2] in y.
    # So the bounding box will be [[0, -2], [120, 2]].
    assert device.xsize == 120, f"X-size mismatch: Expected 120, got {device.xsize}"
    assert device.ysize == 4, f"Y-size mismatch: Expected 4, got {device.ysize}"
    print(f"Device footprint: X={device.xsize} µm, Y={device.ysize} µm (matches constraint [120, 4])")

    # Display the component (requires KLayout or other GDS viewer configured with gdsfactory)
    device.show()

    # You can also write the component to a GDSII file
    # device.write_gds("custom_coupler.gds")

    # Example with different parameters
    # custom_device_2 = custom_coupler(width=0.6, gap_inner=0.3, bend_radius=15, length_io=15, length_bend_x=25, length_coupling=40)
    # custom_device_2.show()
    # print(f"Device 2 footprint: X={custom_device_2.xsize} µm, Y={custom_device_2.ysize} µm")