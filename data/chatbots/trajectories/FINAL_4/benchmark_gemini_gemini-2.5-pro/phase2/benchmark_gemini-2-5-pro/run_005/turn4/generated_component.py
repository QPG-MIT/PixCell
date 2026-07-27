import gdsfactory as gf

@gf.cell
def create_wavy_coupler(
    length: float = 18.0,
    y_max_centerline: float = 1.0,
    y_min_centerline: float = 0.6,
    wg_width: float = 1.0,
):
    """
    Creates a device with two parallel wavy waveguides that are mirror
    images of each other across the x-axis, forming a varying gap.

    The shape is constructed by creating a single "dipping" waveguide from two
    S-bends and then mirroring it for the second arm.

    Args:
        length: The horizontal length of one full wave period.
        y_max_centerline: The maximum vertical position of the top waveguide's centerline.
        y_min_centerline: The minimum vertical position of the top waveguide's centerline.
        wg_width: The width of the waveguides.
    """
    c = gf.Component("wavy_coupler")
    xs = gf.cross_section.cross_section(width=wg_width)

    # 1. Calculate the parameters for the S-bends that will form one "dip".
    # The amplitude of the dip is the total vertical travel of the centerline.
    dip_amplitude = y_max_centerline - y_min_centerline
    s_bend_dx = length / 2.0
    s_bend_dy = dip_amplitude

    # 2. Create a reusable sub-component for a single waveguide arm that dips down.
    # This arm is built to start at y=0, dip to y=-dip_amplitude, and return to y=0.
    arm_unit = gf.Component("wavy_arm_unit")
    bend_down = arm_unit << gf.components.bend_s(
        size=(s_bend_dx, -s_bend_dy), cross_section=xs
    )
    bend_up = arm_unit << gf.components.bend_s(
        size=(s_bend_dx, s_bend_dy), cross_section=xs
    )
    bend_up.connect("o1", bend_down.ports["o2"])

    # Expose the ports of the arm unit for later connection.
    arm_unit.add_port("o1", port=bend_down.ports["o1"])
    arm_unit.add_port("o2", port=bend_up.ports["o2"])

    # 3. Assemble the final device from the arm_unit sub-component.

    # Add the top arm by instantiating the unit and shifting it vertically.
    # It needs to be shifted up so its starting position (y=0) becomes y_max_centerline.
    top_arm = c << arm_unit
    top_arm.movey(y_max_centerline)

    # Add the bottom arm by instantiating the unit, mirroring it, and shifting it down.
    # Mirroring across the x-axis turns the "dip" into a "crest".
    bottom_arm = c << arm_unit
    bottom_arm.mirror(p1=(0, 0), p2=(1, 0))
    
    # Shift the mirrored arm down so its start position (y=0) becomes -y_max_centerline.
    bottom_arm.movey(-y_max_centerline)

    # 4. Add the final component ports from the internal references.
    c.add_port("o1", port=top_arm.ports["o1"])
    c.add_port("o2", port=top_arm.ports["o2"])
    c.add_port("o3", port=bottom_arm.ports["o1"])
    c.add_port("o4", port=bottom_arm.ports["o2"])

    return c


# Main execution block to generate and display the GDS
if __name__ == "__main__":
    # Instantiate the component with parameters calculated to match the
    # target image, which has two separate waveguides.
    # The footprint constraint is [18, 3] um.
    # BBox width = length = 18.0
    # BBox height = 2 * (y_max_centerline + wg_width / 2) = 3.0
    # For wg_width = 1.0, this means 2 * (y_max_centerline + 0.5) = 3.0 -> y_max_centerline = 1.0

    # The previous value of y_min_centerline=0.6 resulted in the waveguides
    # merging. To create a visible gap as seen in the target image, this
    # value must be increased.
    # A value of 0.7 is chosen to create a clear separation.
    # Estimated gap = 2 * y_min_centerline - wg_width = 2 * 0.7 - 1.0 = 0.4 um.
    device = create_wavy_coupler(
        length=18.0,
        y_max_centerline=1.0,
        y_min_centerline=0.7,
        wg_width=1.0,
    )
    device.show()

    # Write the final GDS file
    device.write_gds("wavy_coupler.gds")