import gdsfactory as gf

@gf.cell
def my_coupler(
    waveguide_width: float = 0.5,
    gap: float = 0.2,
    total_length: float = 120.0,
    total_height: float = 4.0,
    straight_io_length: float = 20.0, # Length of straight input/output sections
    coupling_length: float = 20.0,    # Length of the central straight coupling region
    cross_section = None
) -> gf.Component:
    """
    Creates a symmetrical waveguide coupler geometry based on the provided image
    and footprint constraints.

    Args:
        waveguide_width (float): Width of the waveguides.
        gap (float): Minimum gap between the two waveguides in the coupling region.
        total_length (float): Total length of the component in um.
        total_height (float): Total height of the component in um.
        straight_io_length (float): Length of the straight input/output sections.
        coupling_length (float): Length of the central straight coupling region.
        cross_section (gf.CrossSection): Custom cross-section for the waveguides.

    Returns:
        gf.Component: A GDSFactory component representing the coupler.
    """
    c = gf.Component("symmetrical_coupler")

    # Define the default cross-section if not provided
    if cross_section is None:
        cross_section = gf.cross_section.cross_section(width=waveguide_width, layer=(1, 0))

    # Calculate y-coordinates for the centerlines of the waveguides
    y_io_center = total_height / 2 - waveguide_width / 2
    y_coupling_center = gap / 2 + waveguide_width / 2
    
    # Calculate the absolute vertical displacement (dy) for the S-bends
    abs_dy_bend = y_io_center - y_coupling_center

    # Calculate the horizontal displacement (dx) for the S-bends
    # total_length = 2 * straight_io_length + 2 * dx_bend_s + coupling_length
    dx_bend_s = (total_length - 2 * straight_io_length - coupling_length) / 2
    
    if dx_bend_s <= 0:
        raise ValueError(
            "Calculated dx_bend_s is non-positive. "
            "Adjust straight_io_length or coupling_length to be smaller, "
            "or total_length to be larger."
        )
    
    # 1. Create and position the straight input sections (left side)
    wg_top_in = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_bottom_in = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    
    wg_top_in.movey(y_io_center)
    wg_bottom_in.movey(-y_io_center)

    # 2. Create and connect the left S-bends
    # Top path left S-bend: from y_io_center to y_coupling_center (Y decreases), so dy is negative.
    bend_s_left_top = c << gf.components.bend_s(size=(dx_bend_s, -abs_dy_bend), cross_section=cross_section)
    bend_s_left_top.connect("o1", wg_top_in.ports["o2"])

    # Bottom path left S-bend: from -y_io_center to -y_coupling_center (Y increases), so dy is positive.
    bend_s_left_bottom = c << gf.components.bend_s(size=(dx_bend_s, abs_dy_bend), cross_section=cross_section)
    bend_s_left_bottom.connect("o1", wg_bottom_in.ports["o2"])

    # 3. Create and connect the central straight coupling sections
    wg_coupling_top = c << gf.components.straight(length=coupling_length, cross_section=cross_section)
    wg_coupling_bottom = c << gf.components.straight(length=coupling_length, cross_section=cross_section)
    
    wg_coupling_top.connect("o1", bend_s_left_top.ports["o2"])
    wg_coupling_bottom.connect("o1", bend_s_left_bottom.ports["o2"])

    # 4. Create and connect the right S-bends
    # Top path right S-bend: from y_coupling_center to y_io_center (Y increases), so dy is positive.
    bend_s_right_top = c << gf.components.bend_s(size=(dx_bend_s, abs_dy_bend), cross_section=cross_section)
    bend_s_right_top.connect("o1", wg_coupling_top.ports["o2"])

    # Bottom path right S-bend: from -y_coupling_center to -y_io_center (Y decreases), so dy is negative.
    bend_s_right_bottom = c << gf.components.bend_s(size=(dx_bend_s, -abs_dy_bend), cross_section=cross_section)
    bend_s_right_bottom.connect("o1", wg_coupling_bottom.ports["o2"])
    
    # 5. Create and connect the straight output sections (right side)
    wg_top_out = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    wg_bottom_out = c << gf.components.straight(length=straight_io_length, cross_section=cross_section)
    
    wg_top_out.connect("o1", bend_s_right_top.ports["o2"])
    wg_bottom_out.connect("o1", bend_s_right_bottom.ports["o2"])

    # Expose the external ports of the component
    c.add_port("o1", port=wg_top_in.ports["o1"])        # Top left input
    c.add_port("o2", port=wg_bottom_in.ports["o1"])     # Bottom left input
    c.add_port("o3", port=wg_top_out.ports["o2"])       # Top right output
    c.add_port("o4", port=wg_bottom_out.ports["o2"])    # Bottom right output

    return c

# Example usage and verification
if __name__ == "__main__":
    # Instantiate the component with default parameters
    coupler_device = my_coupler()

    # Write the component to a GDSII file
    coupler_device.write_gds("symmetrical_coupler.gds")

    # Optional: Display the component (requires KLayout or similar viewer)
    # gf.show(coupler_device)

    # Verify the footprint of the generated device
    xsize = coupler_device.xmax - coupler_device.xmin
    ysize = coupler_device.ymax - coupler_device.ymin
    print(f"Generated device footprint: X={xsize:.3f} um, Y={ysize:.3f} um")
    
    # Check if the footprint matches the constraint [120, 4]
    assert xsize == 120.0, f"X-size mismatch: Expected 120, Got {xsize}"
    assert ysize == 4.0, f"Y-size mismatch: Expected 4, Got {ysize}"
    print("Footprint matches the constraint.")

    # You can also visualize a specific portion of the component for debugging
    # c_cropped = gf.Component("cropped_view")
    # ref = c_cropped << my_coupler()
    # c_cropped.add_polygon([(0,0),(60,4),(60,0),(0,4)], layer=(1,0)) # Example crop region
    # gf.show(c_cropped)