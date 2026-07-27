import gdsfactory as gf

@gf.cell
def mode_converter_device():
    """
    Parametric recreation of the trident-style mode converter geometry.
    Uses precise length and width constraints derived from the footprint.
    """
    c = gf.Component()

    # --- Constraints & Footprint ---
    # Provided bounding box footprint is [40.0, 1.7]
    total_length = 40.0
    max_width = 1.7

    # --- Parametric Dimensions ---
    # Using even nm equivalents (e.g. 0.02um = 20nm) to prevent DBU symmetry grid crashes
    w_main = 0.50       # 500nm - Main routing waveguide width
    w_tip = 0.02        # 20nm - Thin adiabatic tip (must be an even nm value)
    gap = 0.04          # 40nm - Extremely tight parallel gap 

    # Section Lengths (summing strictly to total_length = 40.0)
    l_in = 2.0          # Left single-mode straight input
    l_taper = 26.0      # Long, dominant adiabatic parallel taper region
    l_sbend = 10.0      # Smooth S-bend expansion region
    l_out = total_length - l_in - l_taper - l_sbend # Remaining straight output (2.0um)

    # --- Layout Logic & Positioning ---
    # Target final separation to achieve exactly 1.7um total width.
    # Total width = 2 * center_y + w_main => center_y = (1.7 - 0.5) / 2 = 0.6
    y_final = (max_width - w_main) / 2.0  

    # Taper placement to maintain exact mathematical parallel constant gap.
    # The outer tapers widen at the exact same rate the inner taper shrinks.
    y_taper = gap + (w_main + w_tip) / 2.0

    # Vertical offset required for the S-bends to reach the final separated width
    dy = y_final - y_taper

    # Default cross section for uniform width routing sections
    xs = gf.cross_section.cross_section(width=w_main, layer=(1, 0))

    # --- 1. Central Waveguide ---
    # Input straight line
    wg_in = c << gf.components.straight(length=l_in, cross_section=xs)
    
    # Central taper down to the thin tip point
    taper_center = c << gf.components.taper(length=l_taper, width1=w_main, width2=w_tip)
    taper_center.connect("o1", wg_in.ports["o2"])

    # --- 2. Top Waveguide ---
    # Outer taper starting from a thin tip growing to full width
    taper_top = c << gf.components.taper(length=l_taper, width1=w_tip, width2=w_main)
    # Move exactly to the start of the taper region, elevated by y_taper
    taper_top.move((0, 0), (l_in, y_taper)) 

    # S-bend smoothly branching outward
    bend_top = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    bend_top.connect("o1", taper_top.ports["o2"])

    # Straight output parallel termination
    out_top = c << gf.components.straight(length=l_out, cross_section=xs)
    out_top.connect("o1", bend_top.ports["o2"])

    # --- 3. Bottom Waveguide ---
    # Mirrored bottom taper
    taper_bot = c << gf.components.taper(length=l_taper, width1=w_tip, width2=w_main)
    taper_bot.move((0, 0), (l_in, -y_taper)) 

    # S-bend smoothly branching outward (negative dy)
    bend_bot = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    bend_bot.connect("o1", taper_bot.ports["o2"])

    # Straight output parallel termination
    out_bot = c << gf.components.straight(length=l_out, cross_section=xs)
    out_bot.connect("o1", bend_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the component device and save the file
    component = mode_converter_device()
    component.write_gds("mode_converter.gds")