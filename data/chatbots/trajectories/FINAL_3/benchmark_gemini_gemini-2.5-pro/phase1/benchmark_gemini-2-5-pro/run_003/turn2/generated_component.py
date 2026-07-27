import gdsfactory as gf

@gf.cell
def coupler_adiabatic_bezier():
    """
    Creates an adiabatic directional coupler using Bezier curves for the
    transition regions, matching the smooth shape of the target image.

    The device geometry is derived from the footprint [120, 4] and visual
    inspection.
    """
    c = gf.Component()

    # Define device parameters based on footprint and typical values
    coupler_length = 60.0   # Length of the central straight coupling section
    bend_length = 30.0      # Horizontal length of each S-bend transition
    port_separation = 4.0   # Vertical center-to-center distance at ports
    width = 0.5             # Waveguide width
    gap = 0.2               # Gap between waveguides in the coupling section

    # Calculate y-coordinates for the centerlines of the waveguides
    # At the ports, the top waveguide is at +port_separation/2
    y_port = port_separation / 2
    # In the coupling region, the center-to-center separation is (width + gap)
    y_coupler = (width + gap) / 2

    # A heuristic for the "straight" portion of the Bezier control polygon.
    # A value of 0.5*bend_length creates a smooth, gentle curve.
    control_length = bend_length * 0.5

    # --- Create the path for the top waveguide ---

    # 1. Define control points for the input Bezier bend.
    # This transitions from the input port y-level to the coupling y-level.
    # The control points are chosen to ensure the path is horizontal at the
    # start and end of the bend, ensuring a smooth connection to the straights.
    points_in = [
        (0, y_port),
        (control_length, y_port),
        (bend_length - control_length, y_coupler),
        (bend_length, y_coupler),
    ]

    # 2. Define control points for the output Bezier bend (symmetric to input)
    x_offset = bend_length + coupler_length
    points_out = [
        (x_offset, y_coupler),
        (x_offset + control_length, y_coupler),
        (x_offset + bend_length - control_length, y_port),
        (x_offset + bend_length, y_port),
    ]

    # 3. Assemble the full path for the top waveguide
    path_top = gf.Path()
    
    # FIX: The Bezier path function is directly under the gf module.
    # Changed gf.path.Bezier to gf.bezier
    path_top.append(gf.bezier(control_points=points_in))
    path_top.append(gf.path.straight(length=coupler_length))
    # FIX: The Bezier path function is directly under the gf module.
    path_top.append(gf.bezier(control_points=points_out))

    # --- Extrude paths and assemble the component ---

    xs = gf.cross_section.cross_section(width=width)

    # Extrude the top path
    wg_top = c << gf.path.extrude(path_top, cross_section=xs)

    # Create the bottom waveguide by extruding the same path and mirroring it
    # across the x-axis.
    wg_bottom = c << gf.path.extrude(path_top, cross_section=xs)
    wg_bottom.mirror(p1=(0, 0), p2=(1, 0))

    # Add the standard four ports for a coupler
    c.add_port("o1", port=wg_top.ports["o1"])
    c.add_port("o2", port=wg_bottom.ports["o1"])
    c.add_port("o3", port=wg_bottom.ports["o2"])
    c.add_port("o4", port=wg_top.ports["o2"])

    return c

# --- Main execution block ---
if __name__ == "__main__":
    # Instantiate the component
    my_device = coupler_adiabatic_bezier()

    # Write the component to a GDS file
    my_device.write_gds("coupler_adiabatic_bezier.gds")

    # Optional: uncomment to view the layout
    # my_device.show(show_ports=True)
    
    print("Successfully generated coupler_adiabatic_bezier.gds")