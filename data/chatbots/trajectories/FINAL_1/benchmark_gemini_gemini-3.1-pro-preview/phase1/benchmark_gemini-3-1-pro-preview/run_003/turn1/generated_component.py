import gdsfactory as gf

@gf.cell
def outer_arm(dy_sign=1):
    """
    Creates one of the outer arms consisting of a taper, an s-bend, and a straight section.
    dy_sign controls whether the S-bend curves upwards (+1) or downwards (-1).
    """
    c = gf.Component()
    
    # Parametric definitions for the arm
    L_taper = 22.5
    w1 = 0.08
    w2 = 0.35
    L_sbend = 9.0
    dy = 0.425 * dy_sign
    L_straight = 6.0

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
    Main assembly cell for the device.
    """
    c = gf.Component()

    # --- Central Prong ---
    # Central taper starts at x=0 and comes to a fine point
    center_taper = c << gf.components.taper(length=25.0, width1=0.4, width2=0.02)

    # --- Top Prong ---
    top_arm = c << outer_arm(dy_sign=1)
    # Positioning exactly to set gap alignment visually identical to the source image
    top_arm.move((2.5, 0.25))

    # --- Bottom Prong ---
    bot_arm = c << outer_arm(dy_sign=-1)
    # Symmetric placement
    bot_arm.move((2.5, -0.25))

    # (Optional) Expose routing ports for hierarchical use
    c.add_port("o1_center", port=center_taper.ports["o1"])
    c.add_port("o2_top", port=top_arm.ports["o2"])
    c.add_port("o3_bot", port=bot_arm.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the geometry component
    device = multi_tip_edge_coupler()
    
    # Write the GDS file to disk (Fixed: Replaced device.show() with write_gds)
    device.write_gds("multi_tip_edge_coupler.gds")