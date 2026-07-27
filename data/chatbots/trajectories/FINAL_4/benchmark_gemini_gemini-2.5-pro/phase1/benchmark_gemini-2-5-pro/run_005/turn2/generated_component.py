import gdsfactory as gf

@gf.cell
def create_eye_coupler(length: float = 25.0, max_separation: float = 6.0, wg_width: float = 0.8):
    """
    Creates an "eye-shaped" or "lens-shaped" coupler where two waveguides
    diverge and then converge back to a single point.

    This is constructed by creating a single curved arm and then mirroring it.
    The arm itself is made of two S-bends connected back-to-back.

    Args:
        length: The total horizontal length of the device.
        max_separation: The maximum vertical separation between the centers of the two arms.
        wg_width: The width of the waveguides.
    """
    # 1. Define the cross-section for the waveguide
    xs = gf.cross_section.cross_section(width=wg_width)

    # 2. Define the parameters for the S-bends that will form one arm.
    # Each arm spans the full length. It consists of two S-bends.
    # The first S-bend goes half the length and reaches the max separation.
    # The second S-bend covers the remaining length, returning to the centerline.
    s_bend_dx = length / 2.0
    s_bend_dy = max_separation / 2.0

    # 3. Create a sub-component for a single arm (the top one).
    # This component will be reused for the bottom arm via mirroring.
    c_arm = gf.Component("top_arm")

    # The first bend curves upwards and outwards.
    bend1 = c_arm << gf.components.bend_s(
        size=(s_bend_dx, s_bend_dy), cross_section=xs
    )
    # The second bend curves downwards and inwards, mirroring the first's vertical travel.
    bend2 = c_arm << gf.components.bend_s(
        size=(s_bend_dx, -s_bend_dy), cross_section=xs
    )

    # Connect the two bends seamlessly to form the complete top arm.
    bend2.connect("o1", bend1.ports["o2"])

    # Add ports to the arm sub-component for later connection.
    c_arm.add_port("o1", port=bend1.ports["o1"])
    c_arm.add_port("o2", port=bend2.ports["o2"])

    # 4. Assemble the final device from the arm sub-component.
    c = gf.Component("eye_coupler_device")

    # Add the top arm as a reference.
    top_arm_ref = c << c_arm

    # Add the bottom arm by creating another reference to the arm
    # and mirroring it across the x-axis.
    bottom_arm_ref = c << c_arm
    bottom_arm_ref.mirror()

    # 5. Add the final component ports. Since the arms start and end at the
    # same points, we only need to expose one set of ports.
    c.add_port("o1", port=top_arm_ref.ports["o1"])
    c.add_port("o2", port=top_arm_ref.ports["o2"])

    return c

# Main execution block to generate and display the GDS
if __name__ == "__main__":
    # Instantiate the component with parameters that match the visual style
    device = create_eye_coupler(length=30, max_separation=8, wg_width=1.2)
    device.show()

    # Write the final GDS file
    device.write_gds("eye_coupler.gds")