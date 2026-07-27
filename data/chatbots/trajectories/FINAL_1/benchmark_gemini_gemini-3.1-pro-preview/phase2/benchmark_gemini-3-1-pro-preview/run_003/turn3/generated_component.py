import gdsfactory as gf

@gf.cell
def outer_arm(dy_sign=1):
    """
    Creates one of the outer arms consisting of a taper, an s-bend, and a straight section.
    dy_sign controls whether the S-bend curves upwards (+1) or downwards (-1).
    """
    c = gf.Component()
    
    # Parametric definitions calculated to exactly match slopes for a constant gap
    L_taper = 20.0
    w1 = 0.10       # Flat, blunt start
    w2 = 0.50       # Thicker final width
    L_sbend = 6.0
    L_straight = 10.0
    
    # Calculate S-bend displacement
    y_start = 0.31 * dy_sign
    y_end = 0.60 * dy_sign
    dy = y_end - y_start

    # 1. Outer arm taper
    taper = c << gf.components.taper(length=L_taper, width1=w1, width2=w2)
    
    # 2. S-bend transition
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
    Main assembly cell. The widths and placements are mathematically aligned
    to ensure the 50nm gaps between the tapers remain perfectly parallel.
    Overall footprint constraints guaranteed: [40.0 x 1.7] um
    """
    c = gf.Component()

    # --- Central Prong ---
    # Width of 0.50 and length of 24.0 yields a slope of exactly 0.01
    center_taper = c << gf.components.taper(length=24.0, width1=0.50, width2=0.02)

    # --- Top Prong ---
    top_arm = c << outer_arm(dy_sign=1)
    # Positioning exactly at x=4.0, y=0.31 guarantees a perfect, constant 0.05um gap
    top_arm.move((4.0, 0.31))

    # --- Bottom Prong ---
    bot_arm = c << outer_arm(dy_sign=-1)
    bot_arm.move((4.0, -0.31))

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