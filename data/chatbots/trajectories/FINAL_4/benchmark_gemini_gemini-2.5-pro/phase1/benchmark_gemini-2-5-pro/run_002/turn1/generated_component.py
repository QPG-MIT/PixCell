import gdsfactory as gf

@gf.cell
def create_wavy_device():
    """
    Creates the wavy device based on the provided image and footprint.

    The device is constructed by creating a single wavy arm from two S-bends
    and then mirroring it to form the symmetric two-arm structure.
    """
    # Parameters derived from footprint [18, 3] and visual analysis
    length = 18.0
    amplitude = 0.3
    width = 0.8
    gap = 0.8

    # Create the top-level component that will hold the final device
    c = gf.Component("wavy_device")

    # Define the cross-section for the waveguide arms
    xs = gf.cross_section.cross_section(width=width)

    # 1. Create a single wavy arm as a separate component for reusability.
    #    This arm is composed of an S-bend going up, followed by an S-bend going down.
    wavy_arm = gf.Component("wavy_arm")
    s_up = wavy_arm << gf.components.bend_s(
        size=(length / 2, amplitude), cross_section=xs
    )
    s_down = wavy_arm << gf.components.bend_s(
        size=(length / 2, -amplitude), cross_section=xs
    )
    s_down.connect("o1", s_up.ports["o2"])
    wavy_arm.add_port("o1", port=s_up.ports["o1"])
    wavy_arm.add_port("o2", port=s_down.ports["o2"])

    # 2. Place the top and bottom arms into the main component 'c'.
    top_arm_ref = c << wavy_arm
    bottom_arm_ref = c << wavy_arm

    # 3. Position the arms to create the final symmetric structure.
    #    The vertical shift is calculated to respect the specified gap.
    y_shift = (gap + width) / 2

    # Move the top arm up
    top_arm_ref.movey(y_shift)

    # Mirror the bottom arm across the x-axis and move it down
    bottom_arm_ref.mirror(p1=(0, 0), p2=(1, 0))
    bottom_arm_ref.movey(-y_shift)
    
    # 4. Add ports to the final component for connectivity.
    c.add_port("o1", port=top_arm_ref.ports["o1"])
    c.add_port("o2", port=bottom_arm_ref.ports["o1"])
    c.add_port("o3", port=top_arm_ref.ports["o2"])
    c.add_port("o4", port=bottom_arm_ref.ports["o2"])

    return c

# This block ensures the script runs when executed directly
if __name__ == "__main__":
    # Instantiate the component
    wavy_device = create_wavy_device()

    # To view the component in a GDS viewer (uncommented for visual feedback)
    wavy_device.show()

    # To save the component to a GDS file
    # FIX: The following line was uncommented to produce the GDS file.
    wavy_device.write_gds("wavy_device.gds")
    
    print("Successfully created and saved wavy_device.gds")