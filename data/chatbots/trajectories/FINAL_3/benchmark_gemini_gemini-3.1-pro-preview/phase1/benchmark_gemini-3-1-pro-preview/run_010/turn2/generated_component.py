import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Directional coupler adjusted to match the visual proportions of the target image,
    strictly maintaining the 120um x 4um bounding box constraint.
    """
    c = gf.Component("directional_coupler")

    # --- Adjusted Parameters for Proportions ---
    # The waveguides are quite thick (~25% of total height each)
    # and the coupling gap is very tight based on the reference image.
    wg_width = 1.0
    gap = 0.2
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Geometry Calculations (Footprint: 120x4) ---
    # Total length = 120
    # Adjusting horizontal segments to match the target's tight bends and long middle section
    l_straight_ends = 10.0
    l_sbend = 15.0
    l_straight_mid = 70.0
    # Verification: 10 + 15 + 70 + 15 + 10 = 120.0 um total length

    # Total height = 4.0 (Top bounding edge at +2.0, Bottom bounding edge at -2.0)
    # y_port is the center line of the input/output ports
    y_port = 2.0 - (wg_width / 2.0)  # 2.0 - 0.5 = 1.5

    # y_mid is the center line of the waveguides in the parallel coupling region
    y_mid = (gap / 2.0) + (wg_width / 2.0)  # 0.1 + 0.5 = 0.6

    # S-bend vertical displacement (for the top arm, it shifts downwards)
    dy_sbend = y_mid - y_port  # 0.6 - 1.5 = -0.9


    # --- Top Arm Construction ---
    top_in = c << gf.components.straight(length=l_straight_ends, cross_section=xs)
    top_in.move((0, y_port))

    top_sbend_in = c << gf.components.bend_s(size=(l_sbend, dy_sbend), cross_section=xs)
    top_sbend_in.connect("o1", top_in.ports["o2"])

    top_mid = c << gf.components.straight(length=l_straight_mid, cross_section=xs)
    top_mid.connect("o1", top_sbend_in.ports["o2"])

    top_sbend_out = c << gf.components.bend_s(size=(l_sbend, -dy_sbend), cross_section=xs)
    top_sbend_out.connect("o1", top_mid.ports["o2"])

    top_out = c << gf.components.straight(length=l_straight_ends, cross_section=xs)
    top_out.connect("o1", top_sbend_out.ports["o2"])


    # --- Bottom Arm Construction ---
    bot_in = c << gf.components.straight(length=l_straight_ends, cross_section=xs)
    bot_in.move((0, -y_port))

    bot_sbend_in = c << gf.components.bend_s(size=(l_sbend, -dy_sbend), cross_section=xs)
    bot_sbend_in.connect("o1", bot_in.ports["o2"])

    bot_mid = c << gf.components.straight(length=l_straight_mid, cross_section=xs)
    bot_mid.connect("o1", bot_sbend_in.ports["o2"])

    bot_sbend_out = c << gf.components.bend_s(size=(l_sbend, dy_sbend), cross_section=xs)
    bot_sbend_out.connect("o1", bot_mid.ports["o2"])

    bot_out = c << gf.components.straight(length=l_straight_ends, cross_section=xs)
    bot_out.connect("o1", bot_sbend_out.ports["o2"])


    # --- Expose External Ports ---
    c.add_port("in1", port=top_in.ports["o1"])
    c.add_port("in2", port=bot_in.ports["o1"])
    c.add_port("out1", port=top_out.ports["o2"])
    c.add_port("out2", port=bot_out.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler_120x4()
    
    # Save the GDS file
    device.write_gds("directional_coupler_120x4.gds")
    
    # Optional: show in KLayout if installed
    device.show()