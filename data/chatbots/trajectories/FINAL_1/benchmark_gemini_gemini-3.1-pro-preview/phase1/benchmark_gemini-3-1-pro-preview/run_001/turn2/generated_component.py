import gdsfactory as gf

@gf.cell
def mode_converter():
    """
    Creates an adiabatic mode converter/coupler structure.
    Constructed using precise parametric sections to match the exact visual 
    proportions and 40.0 x 1.7 footprint.
    """
    c = gf.Component("mode_converter")
    layer = (1, 0)
    
    # ---------------------------------------------------------
    # Geometric Parameters (Total footprint: 40.0 x 1.7 um)
    # ---------------------------------------------------------
    L_in = 4.0      # Section 1: Input straight waveguide length
    L_taper = 18.0  # Section 2: Tapered coupling region length
    L_sbend = 12.0  # Section 3: S-bend routing length
    L_out = 6.0     # Section 4: Straight extension length
    
    w_core = 0.6    # Width of the central waveguide core
    w_arm = 0.5     # Final width of the outer arms
    gap = 0.1       # Gap between core and arms during taper
    
    # Target total bounding width is 1.2 um during the taper section
    w_base = 1.2    

    # ---------------------------------------------------------
    # 1. Section 1: Input Straight Waveguide
    # ---------------------------------------------------------
    # A single waveguide enters from the left before the outer arms appear.
    xs_core = gf.cross_section.cross_section(width=w_core, layer=layer)
    in_wg = c << gf.components.straight(length=L_in, cross_section=xs_core)

    # ---------------------------------------------------------
    # 2. Section 2: Tapered Region via Boolean Cut
    # ---------------------------------------------------------
    # Create a solid bounding block that we will carve the structure out of
    p_taper_base = gf.path.straight(length=L_taper)
    xs_base = gf.cross_section.cross_section(width=w_base, layer=layer)
    taper_base = gf.path.extrude(p_taper_base, cross_section=xs_base)

    xs_gap = gf.cross_section.cross_section(width=gap, layer=layer)

    # Centers of the gap at the start (x=0 relative) and end (x=L_taper relative)
    y_gap_start = 0.35 # (0.3 core top + 0.4 arm inner) / 2
    y_gap_end = 0.05   # (0.0 core tip + 0.1 arm inner) / 2

    # Extend gap paths slightly past the block edges for clean mathematical boolean cuts
    dx = 1.0
    slope = (y_gap_end - y_gap_start) / L_taper
    y_start_ext = y_gap_start - slope * dx
    y_end_ext = y_gap_end + slope * dx

    # Top and bottom cuts
    p_gap_top = gf.Path([(-dx, y_start_ext), (L_taper + dx, y_end_ext)])
    gap_top = gf.path.extrude(p_gap_top, cross_section=xs_gap)

    p_gap_bot = gf.Path([(-dx, -y_start_ext), (L_taper + dx, -y_end_ext)])
    gap_bot = gf.path.extrude(p_gap_bot, cross_section=xs_gap)

    # Boolean subtractions
    taper_step1 = gf.boolean(taper_base, gap_top, operation='not', layer=layer)
    taper_final = gf.boolean(taper_step1, gap_bot, operation='not', layer=layer)

    # Insert into cell and align it perfectly to the end of the input section
    taper_ref = c << taper_final
    taper_ref.movex(L_in)

    # ---------------------------------------------------------
    # 3. Section 3: S-Bend Routing
    # ---------------------------------------------------------
    xs_arm = gf.cross_section.cross_section(width=w_arm, layer=layer)

    # End of taper section leaves outer arms centered at y = ±0.35
    # Total device width is 1.7 -> final arm centers need to be at y = ±0.60
    # Bend dy = 0.60 - 0.35 = 0.25
    dy = 0.25

    bend_top = c << gf.components.bend_s(size=(L_sbend, dy), cross_section=xs_arm)
    bend_top.move((L_in + L_taper, 0.35))

    bend_bot = c << gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs_arm)
    bend_bot.move((L_in + L_taper, -0.35))

    # ---------------------------------------------------------
    # 4. Section 4: Output Straight Extensions
    # ---------------------------------------------------------
    out_wg = gf.components.straight(length=L_out, cross_section=xs_arm)

    out_top = c << out_wg
    out_top.connect("o1", bend_top.ports["o2"])

    out_bot = c << out_wg
    out_bot.connect("o1", bend_bot.ports["o2"])

    # Expose useful external ports
    c.add_port("in", port=in_wg.ports["o1"])
    c.add_port("out_top", port=out_top.ports["o2"])
    c.add_port("out_bot", port=out_bot.ports["o2"])

    return c

if __name__ == "__main__":
    c = mode_converter()
    c.write_gds("mode_converter.gds")