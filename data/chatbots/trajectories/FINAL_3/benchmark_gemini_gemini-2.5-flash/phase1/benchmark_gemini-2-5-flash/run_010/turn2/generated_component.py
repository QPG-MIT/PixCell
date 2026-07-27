import gdsfactory as gf

@gf.cell
def my_crossing(
    waveguide_width: float = 0.5,
    total_length: float = 120.0,
    total_height: float = 4.0,
    straight_io_length: float = 20.0, # Length of straight input/output sections
    cross_section = None
) -> gf.Component:
    """
    Creates a symmetrical waveguide crossing geometry (hourglass shape)
    based on the provided image and footprint constraints.

    Args:
        waveguide_width (float): Width of the waveguides.
        total_length (float): Total length of the component in um.
        total_height (float): Total height of the component in um.
        straight_io_length (float): Length of the straight input/output sections.
        cross_section (gf.CrossSection): Custom cross-section for the waveguides.

    Returns:
        gf.Component: A GDSFactory component representing the crossing.
    """
    c = gf.Component("symmetrical_crossing")

    # Define the default cross-section if not provided
    if cross_section is None:
        cross_section = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))

    # Calculate y-coordinates for the centerlines of the waveguides at input/output.
    # The device height is 4um, and waveguide width is 0.5um.
    # The top waveguide centerline starts at y = 2 - 0.25 = 1.75 um.
    # The bottom waveguide centerline starts at y = -(2 - 0.25) = -1.75 um.
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
    # The top-left path starts at +y_outer_centerline and ends at -y_outer_centerline.
    # The total vertical displacement is -2 * y_outer_centerline.
    # The bottom-left path starts at -y_outer_centerline and ends at +y_outer_centerline.
    # The total vertical displacement is +2 * y_outer_centerline.
    dy_total_crossing = 2 * y_outer_centerline

    # --- Path 1: Top-Left Input to Bottom-Right Output ---
    # 1. Straight input section (top-left)
    wg_tl_in = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_tl_in.movey(y_outer_centerline) # Position the top input waveguide

    # 2. S-bend for crossing. It connects from the end of wg_tl_in to the start of wg_br_out.
    # The 'dy' for this bend is negative as it moves from positive y to negative y.
    crossing_bend_tl_br = c << gf.components.bend_s(
        size=(dx_bend_span, -dy_total_crossing), # dx is total bend span, dy is total vertical displacement
        cross_section=cross_section
    )
    crossing_bend_tl_br.connect("o1", wg_tl_in.ports["o2"]) # Connect to the output of the straight input

    # 3. Straight output section (bottom-right)
    wg_br_out = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_br_out.connect("o1", crossing_bend_tl_br.ports["o2"]) # Connect to the output of the S-bend

    # --- Path 2: Bottom-Left Input to Top-Right Output ---
    # 1. Straight input section (bottom-left)
    wg_bl_in = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_bl_in.movey(-y_outer_centerline) # Position the bottom input waveguide

    # 2. S-bend for crossing. It connects from the end of wg_bl_in to the start of wg_tr_out.
    # The 'dy' for this bend is positive as it moves from negative y to positive y.
    crossing_bend_bl_tr = c << gf.components.bend_s(
        size=(dx_bend_span, dy_total_crossing), # dx is total bend span, dy is total vertical displacement
        cross_section=cross_section
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