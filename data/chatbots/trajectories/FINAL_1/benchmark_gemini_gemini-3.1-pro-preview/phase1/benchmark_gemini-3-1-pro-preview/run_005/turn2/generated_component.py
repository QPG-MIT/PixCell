import gdsfactory as gf

@gf.cell
def adiabatic_mode_splitter() -> gf.Component:
    """
    Parametric recreation of the adiabatic mode splitter.
    Total Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component("adiabatic_mode_splitter")

    # --- Geometric Parameters ---
    total_length = 40.0
    total_width = 1.7
    
    # Section Lengths based on visual proportions
    l_in_straight = 2.5
    l_taper = 22.0
    l_sbend = 9.0
    l_out_straight = total_length - l_in_straight - l_taper - l_sbend  # 6.5 um
    
    # Waveguide Widths
    w_c_in = 0.4
    w_c_out = 0.01       # Central taper narrows to a sharp point
    w_o_out = 0.5        # Final uniform waveguide width for the arms
    
    # To maintain a perfectly constant gap between the central taper and outer tapers,
    # the sum of their widths must be constant if their centerlines are parallel.
    # Formula: w_c_in + w_o_in = w_c_out + w_o_out
    w_o_in = w_o_out + w_c_out - w_c_in  # 0.5 + 0.01 - 0.4 = 0.11
    
    # Y-axis Center Coordinates
    gap = 0.10
    # Outer tapers are offset so their inner edge is `gap` away from central taper
    y_outer_taper = gap + (w_c_in + w_o_in) / 2  # 0.1 + 0.255 = 0.355
    y_straight = total_width / 2 - w_o_out / 2   # 1.7/2 - 0.25 = 0.60
    
    layer = (1, 0)
    xs_outer = gf.cross_section.cross_section(width=w_o_out, layer=layer)
    xs_center_in = gf.cross_section.cross_section(width=w_c_in, layer=layer)

    # --- 1. Central Structure ---
    # Input straight section (this extends to the left of the outer arms)
    in_straight = c << gf.components.straight(
        length=l_in_straight,
        cross_section=xs_center_in
    )
    
    # Central tapering section
    c_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_c_in,
        width2=w_c_out,
        layer=layer
    )
    c_taper.connect("o1", in_straight.ports["o2"])

    # --- 2. Top Arm Construction ---
    # Outer taper segment
    top_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_o_in,
        width2=w_o_out,
        layer=layer
    )
    # Align the start of the outer taper with the start of the central taper
    top_taper.movex(l_in_straight)
    top_taper.movey(y_outer_taper)

    # S-Bend outward divergence
    dy_top = y_straight - y_outer_taper
    top_sbend = c << gf.components.bend_s(
        size=(l_sbend, dy_top),
        cross_section=xs_outer
    )
    top_sbend.connect("o1", top_taper.ports["o2"])

    # Straight output
    top_straight = c << gf.components.straight(
        length=l_out_straight,
        cross_section=xs_outer
    )
    top_straight.connect("o1", top_sbend.ports["o2"])

    # --- 3. Bottom Arm Construction ---
    # Outer taper segment
    bot_taper = c << gf.components.taper(
        length=l_taper,
        width1=w_o_in,
        width2=w_o_out,
        layer=layer
    )
    # Align with the central taper start
    bot_taper.movex(l_in_straight)
    bot_taper.movey(-y_outer_taper)

    # S-Bend outward divergence (negative dy)
    dy_bot = -y_straight - (-y_outer_taper)
    bot_sbend = c << gf.components.bend_s(
        size=(l_sbend, dy_bot),
        cross_section=xs_outer
    )
    bot_sbend.connect("o1", bot_taper.ports["o2"])

    # Straight output
    bot_straight = c << gf.components.straight(
        length=l_out_straight,
        cross_section=xs_outer
    )
    bot_straight.connect("o1", bot_sbend.ports["o2"])

    return c

if __name__ == "__main__":
    device = adiabatic_mode_splitter()
    device.write_gds("adiabatic_mode_splitter.gds")