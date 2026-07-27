import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec

# Custom S-bend function using gf.path.smooth for Euler-like bends
@gf.cell
def custom_s_bend_euler_like(
    size: tuple[float, float],
    cross_section: CrossSectionSpec = "strip",
    bend_radius: float | None = None, # Minimum bend radius for the internal Euler bends
) -> gf.Component:
    """
    Creates an S-bend from two Euler-like bends using gf.path.smooth.
    The path is defined by three points: start, mid (inflection point), and end.
    gf.path.smooth connects these points with Euler-like curves.

    Args:
        size (tuple[float, float]): (dx, dy) total horizontal and vertical displacement.
        cross_section (CrossSectionSpec): Cross-section specification.
        bend_radius (float | None): Minimum bend radius for the Euler bends.
            If None, a default is calculated based on `dy`.
    """
    c = gf.Component()
    dx, dy = size
    xs = gf.get_cross_section(cross_section)

    if bend_radius is None:
        # Heuristic for a reasonable bend radius based on the geometry.
        # It should be large enough to allow for smooth transitions
        # and typically related to the waveguide width or the total vertical displacement.
        # We ensure it's at least twice the waveguide width for practical reasons,
        # and proportional to dy for aesthetic scaling, capped at 20um to prevent excessively large radii.
        bend_radius = max(xs.width * 2, abs(dy) * 1.5)
        bend_radius = min(bend_radius, 20.0) # Cap at 20um for typical devices

    # Define points for an S-curve. The `smooth` function will connect these with Euler bends.
    # The mid-point `(dx / 2, dy / 2)` acts as the inflection point.
    points = [
        (0, 0),
        (dx / 2, dy / 2),
        (dx, dy),
    ]

    # CORRECTED: Call gf.path.smooth directly with the points list
    # This returns a new Path object with smoothed segments.
    smoothed_path = gf.path.smooth(points, radius=bend_radius)

    # Extrude the smoothed path and add it as a reference to the current component `c`.
    path_component_ref = c << gf.path.extrude(smoothed_path, cross_section=xs)

    # Add ports from the reference to the main component `c`.
    c.add_port("o1", port=path_component_ref.ports["o1"])
    c.add_port("o2", port=path_component_ref.ports["o2"])

    # FIX: Flatten the component before returning it.
    # This converts all internal references to raw polygons and snaps them to the grid,
    # ensuring that the component itself is grid-aligned when instantiated elsewhere.
    c.flatten()

    return c

@gf.cell
def my_crossing(
    waveguide_width: float = 0.5,
    total_length: float = 120.0,
    total_height: float = 4.0,
    straight_io_length: float = 20.0, # Length of straight input/output sections
    crossing_bend_radius: float | None = None, # Specific bend radius for the S-bends
    cross_section = None
) -> gf.Component:
    """
    Creates a symmetrical waveguide crossing geometry (hourglass shape)
    based on the provided image and footprint constraints, using Euler-like S-bends.

    Args:
        waveguide_width (float): Width of the waveguides.
        total_length (float): Total length of the component in um.
        total_height (float): Total height of the component in um.
        straight_io_length (float): Length of the straight input/output sections.
        crossing_bend_radius (float | None): Minimum bend radius for the S-bends.
                                             If None, a default is calculated by custom_s_bend_euler_like.
        cross_section (gf.CrossSection): Custom cross-section for the waveguides.

    Returns:
        gf.Component: A GDSFactory component representing the crossing.
    """
    c = gf.Component("symmetrical_crossing")

    # Define the default cross-section if not provided
    if cross_section is None:
        cross_section = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))

    # Calculate y-coordinates for the centerlines of the waveguides at input/output.
    # The total_height (4um) minus the waveguide_width (0.5um) is the space between outer edges.
    # Half of this defines the centerline offset from the component's center for input/output.
    # e.g., for total_height=4, width=0.5, y_outer_centerline = (4/2) - (0.5/2) = 2 - 0.25 = 1.75 um.
    y_outer_centerline = total_height / 2 - waveguide_width / 2

    # Calculate the total horizontal span for the S-bend sections.
    # This is the total length minus the two straight input/output sections.
    dx_bend_span = total_length - 2 * straight_io_length
    
    if dx_bend_span <= 0:
        raise ValueError(
            "Calculated dx_bend_span is non-positive. "
            "Adjust straight_io_length to be smaller, or total_length to be larger."
        )
    
    # Calculate the total vertical displacement for each crossing path.
    # For a symmetrical crossing, this is twice the y_outer_centerline.
    dy_total_crossing = 2 * y_outer_centerline

    # --- Path 1: Top-Left Input to Bottom-Right Output ---
    # 1. Straight input section (top-left)
    wg_tl_in = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_tl_in.movey(y_outer_centerline) # Position the top input waveguide

    # 2. S-bend for crossing.
    #    Using the new custom_s_bend_euler_like for smoother curvature.
    #    The 'dy' for this bend is negative as it moves from positive y to negative y.
    crossing_bend_tl_br = c << custom_s_bend_euler_like(
        size=(dx_bend_span, -dy_total_crossing), # dx is total bend span, -dy for downward movement
        cross_section=cross_section,
        bend_radius=crossing_bend_radius # Pass through custom bend radius
    )
    crossing_bend_tl_br.connect("o1", wg_tl_in.ports["o2"]) # Connect to the output of the straight input

    # 3. Straight output section (bottom-right)
    wg_br_out = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_br_out.connect("o1", crossing_bend_tl_br.ports["o2"]) # Connect to the output of the S-bend

    # --- Path 2: Bottom-Left Input to Top-Right Output ---
    # 1. Straight input section (bottom-left)
    wg_bl_in = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_bl_in.movey(-y_outer_centerline) # Position the bottom input waveguide

    # 2. S-bend for crossing.
    #    Using the new custom_s_bend_euler_like for smoother curvature.
    #    The 'dy' for this bend is positive as it moves from negative y to positive y.
    crossing_bend_bl_tr = c << custom_s_bend_euler_like(
        size=(dx_bend_span, dy_total_crossing), # dx is total bend span, +dy for upward movement
        cross_section=cross_section,
        bend_radius=crossing_bend_radius # Pass through custom bend radius
    )
    crossing_bend_bl_tr.connect("o1", wg_bl_in.ports["o2"]) # Connect to the output of the straight input

    # 3. Straight output section (top-right)
    wg_tr_out = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_tr_out.connect("o1", crossing_bend_bl_tr.ports["o2"]) # Connect to the output of the S-bend

    # Expose the external ports of the component for easy connection to other devices
    c.add_port("o1", port=wg_tl_in.ports["o1"])        # Top left input port
    c.add_port("o2", port=wg_bl_in.ports["o1"])        # Bottom left input port
    c.add_port("o3", port=wg_br_out.ports["o2"])       # Bottom right output port (from top-left input)
    c.add_port("o4", port=wg_tr_out.ports["o2"])       # Top right output port (from bottom-left input)

    return c

# Example usage and verification
if __name__ == "__main__":
    # Instantiate the component with default parameters
    crossing_device = my_crossing()

    # Write the component to a GDSII file
    crossing_device.write_gds("symmetrical_crossing.gds")

    # Verify the footprint of the generated device
    xsize = crossing_device.xmax - crossing_device.xmin
    ysize = crossing_device.ymax - crossing_device.ymin
    print(f"Generated device footprint: X={xsize:.3f} um, Y={ysize:.3f} um")
    
    # Check if the footprint matches the constraint [120, 4]
    assert xsize == 120.0, f"X-size mismatch: Expected 120, Got {xsize}"
    assert ysize == 4.0, f"Y-size mismatch: Expected 4, Got {ysize}"
    print("Footprint matches the constraint.")

    # Optional: Display the component in a GDS viewer (e.g., KLayout)
    # gf.show(crossing_device)