import gdsfactory as gf

@gf.cell
def directional_coupler_reconstruction():
    """
    Recreates the symmetric coupler geometry from the image.
    Footprint target: 120um x 4um
    """
    c = gf.Component("directional_coupler")

    # 1. Define the Cross-Section
    # Standard 500nm wide waveguide for telecom wavelengths
    width = 0.5
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # 2. Geometric Parameters calculated for the footprint
    # Total length = coupler_length + 2 * arm_dx = 120um
    # Total width = 2 * (gap/2 + width/2 + arm_dy) = 4um
    coupler_length = 60.0
    gap = 0.2
    arm_dx = 30.0  # (120 - 60) / 2
    arm_dy = 1.45  # Centers the ports within the 4um height limit

    # 3. Create the central coupling region
    # This primitive creates two parallel waveguides with a fixed gap.
    coupler = c << gf.components.coupler_straight(
        length=coupler_length, 
        gap=gap, 
        cross_section=xs
    )

    # 4. Create the S-bend transition arms
    # bend_s creates an S-shaped curve of given width (dx) and height (dy).
    sbend = gf.components.bend_s(size=(arm_dx, arm_dy), cross_section=xs)

    # 5. Assemble the device by connecting ports
    # Port map for coupler_straight: 
    # o1: Bottom-Left, o2: Top-Left, o3: Top-Right, o4: Bottom-Right

    # Left Side Transitions
    bl_arm = c << sbend
    bl_arm.connect("o1", coupler.ports["o1"]) # Standard S-bend goes 'down'

    tl_arm = c << sbend
    tl_arm.mirror() # Mirror vertically so it goes 'up'
    tl_arm.connect("o1", coupler.ports["o2"])

    # Right Side Transitions
    br_arm = c << sbend
    br_arm.connect("o1", coupler.ports["o4"]) # Standard S-bend goes 'down'

    tr_arm = c << sbend
    tr_arm.mirror() # Mirror vertically so it goes 'up'
    tr_arm.connect("o1", coupler.ports["o3"])

    # 6. Expose the external ports for the top-level component
    c.add_port("o1", port=bl_arm.ports["o2"])
    c.add_port("o2", port=tl_arm.ports["o2"])
    c.add_port("o3", port=tr_arm.ports["o2"])
    c.add_port("o4", port=br_arm.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate and show the component
    device = directional_coupler_reconstruction()
    device.show()
    
    # Verify footprint
    print(f"Component size: {device.size_info.width} x {device.size_info.height} um")
    device.write_gds("symmetric_coupler.gds")