import gdsfactory as gf

@gf.cell
def wavy_arm(length: float = 9.0, amplitude: float = 0.9, cross_section="strip"):
    """
    Creates a single wavy waveguide component resembling one period of a sine wave.
    This is achieved by connecting two S-bends.

    Args:
        length: The horizontal length of a single S-bend (half the total period).
        amplitude: The vertical displacement of the S-bend.
        cross_section: The cross-section to extrude the path.
    """
    c = gf.Component()
    xs = gf.get_cross_section(cross_section)

    # A full wave period is created by one S-bend going up and one going down.
    s_bend1 = gf.components.bend_s(size=(length, amplitude), cross_section=xs)
    s_bend2 = gf.components.bend_s(size=(length, -amplitude), cross_section=xs)
    
    # Add and connect the two S-bends
    ref1 = c << s_bend1
    ref2 = c << s_bend2
    ref2.connect("o1", ref1.ports["o2"])

    # Add ports to the combined wavy arm
    c.add_port("o1", port=ref1.ports["o1"])
    c.add_port("o2", port=ref2.ports["o2"])
    return c

@gf.cell
def recreate_device():
    """
    Recreates the wavy structure from the image based on the provided
    footprint of [18, 3] um.

    The device is built by placing two mirrored instances of a basic
    wavy arm component.
    """
    c = gf.Component()

    # --- 1. Derive Parameters from Footprint and Assumptions ---
    footprint_width = 18.0
    footprint_height = 3.0
    wg_width = 0.5  # Assumed standard waveguide width
    gap_at_ends = 0.2  # Assumed minimum gap where arms are closest

    # Calculate the vertical shift for each arm from the centerline (y=0)
    # 2 * vertical_shift = gap_at_ends + wg_width
    vertical_shift = (gap_at_ends + wg_width) / 2
    
    # Calculate the wave amplitude needed to meet the total height constraint
    # (amplitude + vertical_shift) + wg_width/2 = footprint_height/2
    amplitude = (footprint_height / 2) - vertical_shift - (wg_width / 2)

    # Each S-bend covers half the total length
    s_bend_length = footprint_width / 2

    # --- 2. Define Cross-Section ---
    xs = gf.cross_section.cross_section(width=wg_width)

    # --- 3. Assemble the Device ---
    # Create the basic building block: a single wavy arm
    base_arm = wavy_arm(
        length=s_bend_length, amplitude=amplitude, cross_section=xs
    )
    
    # Create and place the top arm
    top_arm_ref = c << base_arm
    top_arm_ref.movey(vertical_shift)
    
    # Create, mirror, and place the bottom arm
    bottom_arm_ref = c << base_arm
    bottom_arm_ref.mirror(p1=(0, 0), p2=(1, 0))  # Mirror across the x-axis
    bottom_arm_ref.movey(-vertical_shift)
    
    # Center the final component at (0, 0)
    c.movex(-footprint_width / 2)
    
    return c

# Main execution block to instantiate and save the GDS file
if __name__ == "__main__":
    # Instantiate the final component
    device = recreate_device()
    
    # Show the component in a viewer (like KLayout)
    device.show()
    
    # Write the component to a GDS file
    device.write_gds("recreated_device.gds")