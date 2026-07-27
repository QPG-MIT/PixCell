import gdsfactory as gf

@gf.cell
def coupler_segmented_interaction_v2():
    """
    Corrected recreation of the segmented directional coupler.
    Improvements:
    - Aligned inner floating waveguides with outer arm straight sections.
    - Enforced uniform gaps and widths for the 5 parallel lines in the center.
    - Adjusted length ratios to match the original image.
    """
    c = gf.Component()

    # =======================================================================
    # Parameters
    # =======================================================================
    # 1. Footprint Dimensions
    length_total = 120.0
    
    # 2. Waveguide & Grid Dimensions
    # To create the "solid block" look of 5 lines, we need tight packing.
    wg_width = 0.5
    gap = 0.2
    pitch = wg_width + gap  # Center-to-center vertical distance (0.7um)

    # 3. Length Partitions
    # Visual analysis suggests the straight section is dominant.
    # We allocate 70um for interaction, leaving 25um for each S-bend.
    length_straight = 70.0
    length_bend = (length_total - length_straight) / 2  # Results in 25.0

    # 4. Vertical Positions (Y-coordinates)
    # The center stack has 5 lines: 0 (mid), +/- 1 pitch, +/- 2 pitches
    y_center = 0
    y_float_top = pitch           # +0.7
    y_float_bot = -pitch          # -0.7
    y_outer_straight_top = 2 * pitch  # +1.4 (Top Arm straight section)
    y_outer_straight_bot = -2 * pitch # -1.4 (Bot Arm straight section)

    # Input/Output Ports (Outer edges)
    # The arms bend outwards to these positions.
    y_input_top = 1.8
    y_input_bot = -1.8

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # =======================================================================
    # 1. Inner Floating Waveguides (The 3 Center Bars)
    # =======================================================================
    # Create the straight segment component
    wg_segment = gf.components.straight(length=length_straight, cross_section=xs)

    # Place Middle Bar
    ref_mid = c << wg_segment
    ref_mid.center = (length_total / 2, y_center)

    # Place Upper Floating Bar
    ref_float_top = c << wg_segment
    ref_float_top.center = (length_total / 2, y_float_top)

    # Place Lower Floating Bar
    ref_float_bot = c << wg_segment
    ref_float_bot.center = (length_total / 2, y_float_bot)

    # =======================================================================
    # 2. Top Outer Arm
    # =======================================================================
    # Calculate S-bend vertical offset
    # Top arm moves from y_input_top (1.8) -> y_outer_straight_top (1.4)
    dy_top = y_outer_straight_top - y_input_top  # Negative offset

    # Top Input S-Bend
    t_in = c << gf.components.bend_s(size=(length_bend, dy_top), cross_section=xs)
    t_in.move((0, y_input_top)) # Move start point to (0, 1.8)

    # Top Straight Section
    t_mid = c << gf.components.straight(length=length_straight, cross_section=xs)
    t_mid.connect("o1", t_in.ports["o2"])

    # Top Output S-Bend (Symmetric to input, but bending back up)
    t_out = c << gf.components.bend_s(size=(length_bend, -dy_top), cross_section=xs)
    t_out.connect("o1", t_mid.ports["o2"])

    # =======================================================================
    # 3. Bottom Outer Arm
    # =======================================================================
    # Bottom arm moves from y_input_bot (-1.8) -> y_outer_straight_bot (-1.4)
    dy_bot = y_outer_straight_bot - y_input_bot  # Positive offset

    # Bottom Input S-Bend
    b_in = c << gf.components.bend_s(size=(length_bend, dy_bot), cross_section=xs)
    b_in.move((0, y_input_bot))

    # Bottom Straight Section
    b_mid = c << gf.components.straight(length=length_straight, cross_section=xs)
    b_mid.connect("o1", b_in.ports["o2"])

    # Bottom Output S-Bend
    b_out = c << gf.components.bend_s(size=(length_bend, -dy_bot), cross_section=xs)
    b_out.connect("o1", b_mid.ports["o2"])

    # =======================================================================
    # Ports
    # =======================================================================
    c.add_port("o1", port=t_in.ports["o1"])
    c.add_port("o2", port=b_in.ports["o1"])
    c.add_port("o3", port=t_out.ports["o2"])
    c.add_port("o4", port=b_out.ports["o2"])

    return c

# Generate and show
device = coupler_segmented_interaction_v2()
device.show()
device.write_gds("segmented_coupler_v2.gds")