import gdsfactory as gf

@gf.cell
def create_directional_coupler():
    """
    Creates a directional coupler with two parallel waveguides.

    The device consists of two S-bends bringing the waveguides together,
    a straight parallel coupling section, and two S-bends separating them again.
    This is a "pass-through" or non-crossing configuration.
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
    c = gf.Component("directional_coupler")
    xs = gf.cross_section.cross_section(width=wg_width)

    # Define the primitive components we will use.
    s_bend = gf.components.bend_s(size=(s_bend_dx, s_bend_dy), cross_section=xs)
    straight = gf.components.straight(length=coupling_length, cross_section=xs)

    # Instantiate all the necessary building blocks as references.
    s_bend_in_top = c << s_bend
    s_bend_in_bot = c << s_bend
    straight_top = c << straight
    straight_bot = c << straight
    s_bend_out_top = c << s_bend
    s_bend_out_bot = c << s_bend

    # --- 3. Orientation and Connection ---
    # A standard s_bend goes from low-y to high-y. We mirror some vertically
    # to create bends that go from high-y to low-y.
    s_bend_in_top.mirror_y()  # Input bend moves downwards.
    s_bend_out_bot.mirror_y() # Output bend moves downwards.

    # Position the start of the two independent waveguide paths.
    # The input port separation is `port_separation_y` centered at y=0.
    s_bend_in_top.movey(port_separation_y / 2)
    s_bend_in_bot.movey(-port_separation_y / 2)

    # Connect the primitives to form the top waveguide path.
    straight_top.connect("o1", s_bend_in_top.ports["o2"])
    s_bend_out_top.connect("o1", straight_top.ports["o2"])

    # Connect the primitives to form the bottom waveguide path.
    straight_bot.connect("o1", s_bend_in_bot.ports["o2"])
    s_bend_out_bot.connect("o1", straight_bot.ports["o2"])

    # --- 4. Port Definition ---
    # Expose the external ports of the final component.
    c.add_port("o1", port=s_bend_in_top.ports["o1"])   # Top-left
    c.add_port("o2", port=s_bend_in_bot.ports["o1"])   # Bottom-left
    c.add_port("o3", port=s_bend_out_top.ports["o2"])  # Top-right
    c.add_port("o4", port=s_bend_out_bot.ports["o2"])  # Bottom-right

    return c

if __name__ == "__main__":
    # Create an instance of the device cell.
    device = create_directional_coupler()
    
    # Write the component geometry to a GDSII file.
    device.write_gds("directional_coupler.gds")

    # Optional: Display the component in the KLayout-based viewer.
    device.show()