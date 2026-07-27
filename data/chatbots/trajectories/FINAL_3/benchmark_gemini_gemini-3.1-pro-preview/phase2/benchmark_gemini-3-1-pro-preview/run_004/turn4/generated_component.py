import gdsfactory as gf

@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component("directional_coupler")

    # Waveguide cross-section
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Redistributed length constraints to match the target's visual proportions
    # The target image has smooth, elongated S-bends and shorter input arms.
    # 15 + 25 + 40 + 25 + 15 = 120 um total length exactly
    l_in = 15.0      # Shorter input/output straight length
    l_sbend = 25.0   # Significantly longer S-bend for a gentler transition
    l_mid = 40.0     # Coupling region straight length
    
    # Height constraints for exactly 4 um footprint (unchanged)
    # Total height = max Y (2.0) - min Y (-2.0) = 4.0 um
    y_outer = 1.75
    y_inner = 0.35
    dy = y_outer - y_inner  # 1.4 um S-bend vertical transition

    # ==========================
    # Top Arm Assembly
    # ==========================
    st_in_top = c << gf.components.straight(length=l_in, cross_section=xs)
    sb_in_top = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    st_mid_top = c << gf.components.straight(length=l_mid, cross_section=xs)
    sb_out_top = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    st_out_top = c << gf.components.straight(length=l_in, cross_section=xs)

    # Position and connect top arm
    st_in_top.move((0, y_outer))
    sb_in_top.connect("o1", st_in_top.ports["o2"])
    st_mid_top.connect("o1", sb_in_top.ports["o2"])
    sb_out_top.connect("o1", st_mid_top.ports["o2"])
    st_out_top.connect("o1", sb_out_top.ports["o2"])

    # ==========================
    # Bottom Arm Assembly
    # ==========================
    st_in_bot = c << gf.components.straight(length=l_in, cross_section=xs)
    sb_in_bot = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    st_mid_bot = c << gf.components.straight(length=l_mid, cross_section=xs)
    sb_out_bot = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    st_out_bot = c << gf.components.straight(length=l_in, cross_section=xs)

    # Position and connect bottom arm
    st_in_bot.move((0, -y_outer))
    sb_in_bot.connect("o1", st_in_bot.ports["o2"])
    st_mid_bot.connect("o1", sb_in_bot.ports["o2"])
    sb_out_bot.connect("o1", st_mid_bot.ports["o2"])
    st_out_bot.connect("o1", sb_out_bot.ports["o2"])

    # Add logical ports to the assembled component
    c.add_port("o1", port=st_in_top.ports["o1"])
    c.add_port("o2", port=st_in_bot.ports["o1"])
    c.add_port("o3", port=st_out_top.ports["o2"])
    c.add_port("o4", port=st_out_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Instantiate the component
    c = directional_coupler()
    
    # Save the component to a GDS file
    c.write_gds("directional_coupler.gds")