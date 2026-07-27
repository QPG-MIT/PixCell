import gdsfactory as gf

@gf.cell
def create_waveguide_crossing_coupler():
    """
    Creates a waveguide crossing device based on the target image.

    This device features an input crossing, a parallel straight section,
    and an output Y-split, constructed from S-bend and straight primitives.
    """
    # --- 1. Parameter Definition ---
    # Derived from an assumed footprint of [120, 4] um and visual analysis.
    footprint_x = 120.0
    footprint_y = 4.0
    wg_width = 0.5
    gap_center = 0.2

    # Lengths of the different sections of the device.
    coupling_length = 20.0
    s_bend_dx = (footprint_x - coupling_length) / 2.0

    # Vertical separation of waveguides at the center and at the ports.
    center_separation_y = wg_width + gap_center
    port_separation_y = footprint_y - wg_width

    # Vertical displacement required for each S-bend.
    s_bend_dy = (port_separation_y - center_separation_y) / 2.0

    # --- 2. Component Assembly ---
    c = gf.Component("waveguide_crossing_coupler")
    xs = gf.cross_section.cross_section(width=wg_width)

    # Define the primitive components we will use.
    s_bend = gf.components.bend_s(size=(s_bend_dx, s_bend_dy), cross_section=xs)
    straight = gf.components.straight(length=coupling_length, cross_section=xs)

    # Instantiate all the necessary building blocks as references.
    # Left side (crossing bends)
    b_cross_top_to_bot = c << s_bend
    b_cross_bot_to_top = c << s_bend

    # Right side (splitting bends)
    b_split_top = c << s_bend
    b_split_bot = c << s_bend

    # Center straight sections
    s_top = c << straight
    s_bot = c << straight

    # --- 3. Orientation and Connection ---
    # A standard s_bend goes from low-y to high-y. We mirror it vertically
    # to create a bend that goes from high-y to low-y.
    b_cross_top_to_bot.mirror_y()
    b_split_bot.mirror_y()

    # Assemble the two paths by connecting the primitives end-to-end.
    # The `connect` command also handles positioning.

    # Path 1 (Bottom): Connects top-left port to bottom-right port.
    s_bot.connect("o1", b_cross_top_to_bot.ports["o2"])
    b_split_bot.connect("o1", s_bot.ports["o2"])

    # Path 2 (Top): Connects bottom-left port to top-right port.
    # We must explicitly place the start of this path to align with the first one.
    b_cross_bot_to_top.y = -b_cross_top_to_bot.y
    s_top.connect("o1", b_cross_bot_to_top.ports["o2"])
    b_split_top.connect("o1", s_top.ports["o2"])

    # --- 4. Port Definition ---
    # Expose the external ports of the final component.
    c.add_port("o1", port=b_cross_top_to_bot.ports["o1"])  # Top-left
    c.add_port("o2", port=b_cross_bot_to_top.ports["o1"])  # Bottom-left
    c.add_port("o3", port=b_split_top.ports["o2"])        # Top-right
    c.add_port("o4", port=b_split_bot.ports["o2"])        # Bottom-right

    return c

if __name__ == "__main__":
    # Create an instance of the device cell.
    device = create_waveguide_crossing_coupler()
    
    # Write the component geometry to a GDSII file.
    device.write_gds("waveguide_crossing.gds")

    # Optional: Display the component in the KLayout-based viewer.
    device.show()