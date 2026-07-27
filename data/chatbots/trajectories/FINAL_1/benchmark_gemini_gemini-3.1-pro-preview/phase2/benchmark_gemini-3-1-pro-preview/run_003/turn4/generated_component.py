import gdsfactory as gf

@gf.cell
def outer_arm(dy_sign=1):
    """
    Creates one of the outer arms consisting of a taper, an s-bend, and a straight section.
    dy_sign controls whether the S-bend curves upwards (+1) or downwards (-1).
    """
    c = gf.Component()
    
    # Refined parametric definitions for a smoother bend
    L_taper = 18.0
    w1 = 0.10
    w2 = 0.50
    L_sbend = 8.0
    L_straight = 10.0
    
    # Exact calculation to maintain a constant 50nm gap with the central taper
    y_start = (27.5 / 90.0) * dy_sign  # ~0.30556
    y_end = 0.60 * dy_sign
    dy = y_end - y_start

    # 1. Outer arm taper
    taper = c << gf.components.taper(length=L_taper, width1=w1, width2=w2)
    
    # 2. S-bend transition (longer for a smoother cosine curve)
    xs = gf.cross_section.cross_section(width=w2)
    sbend = c << gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    sbend.connect("o1", taper.ports["o2"])

    # 3. Final straight waveguide
    straight = c << gf.components.straight(length=L_straight, cross_section=xs)
    straight.connect("o1", sbend.ports["o2"])

    c.add_port("o1", port=taper.ports["o1"])
    c.add_port("o2", port=straight.ports["o2"])
    
    return c

@gf.cell
def multi_tip_edge_coupler():
    """
    Main assembly cell.
    Footprint constraints strictly guaranteed: [40.0 x 1.7] um.
    """
    c = gf.Component()

    # --- Central Prong ---
    # Length exactly 22.0 aligns the tip perfectly with the start of the S-bends
    L_c = 22.0
    w_c1 = 0.50
    # End width calculated to perfectly match the taper slope of the outer arms
    w_c2 = 0.50 - 44.0 / 90.0  # ~0.0111
    
    center_taper = c << gf.components.taper(length=L_c, width1=w_c1, width2=w_c2)

    # --- Top Prong ---
    top_arm = c << outer_arm(dy_sign=1)
    top_arm.move((4.0, 27.5 / 90.0))

    # --- Bottom Prong ---
    bot_arm = c << outer_arm(dy_sign=-1)
    bot_arm.move((4.0, -27.5 / 90.0))

    # Expose routing ports
    c.add_port("o1_center", port=center_taper.ports["o1"])
    c.add_port("o2_top", port=top_arm.ports["o2"])
    c.add_port("o3_bot", port=bot_arm.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the refined geometry component
    device = multi_tip_edge_coupler()
    
    # Write the GDS file to disk
    device.write_gds("multi_tip_edge_coupler.gds")