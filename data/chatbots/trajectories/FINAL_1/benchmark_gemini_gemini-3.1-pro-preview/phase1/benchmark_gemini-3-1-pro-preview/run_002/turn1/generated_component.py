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
    # Inferred from visual proportions to maintain a total width of 1.7
    w_main = 0.45       # Standard routing waveguide width
    w_tip = 0.1         # Adiabatic transition thin tip width
    gap = 0.1           # Constant gap between waveguides in the taper section

    # Lengths of distinct sections (must sum to total_length = 40.0)
    l_in = 3.0          # Left single-mode straight input
    l_taper = 24.0      # Adiabatic parallel taper coupling region
    l_sbend = 8.0       # S-bend expansion region
    l_out = total_length - l_in - l_taper - l_sbend # Remaining straight output

    # --- Layout Logic & Positioning ---
    # Target final separation (center-to-center) to achieve exactly 1.7um total width
    y_final = (max_width - w_main) / 2.0  

    # Taper placement to maintain exact constant gap 'g' throughout the coupling region.
    # Because outer widths grow by the exact amount the inner width shrinks, 
    # holding center distance constant creates parallel edges.
    y_taper = (w_main / 2.0) + gap + (w_tip / 2.0)

    # Vertical offset required for the S-bends to reach the final width
    dy = y_final - y_taper

    # Default cross section for uniform width sections
    xs = gf.cross_section.cross_section(width=w_main, layer=(1, 0))

    # --- 1. Central Waveguide ---
    # Input straight line
    wg_in = c << gf.components.straight(length=l_in, cross_section=xs)
    
    # Central taper down to a point (ends after coupling region)
    taper_center = c << gf.components.taper(length=l_taper, width1=w_main, width2=w_tip)
    taper_center.connect("o1", wg_in.ports["o2"])

    # --- 2. Top Waveguide ---
    # Outer taper starting from a thin tip to full width
    taper_top = c << gf.components.taper(length=l_taper, width1=w_tip, width2=w_main)
    # Move port 'o1' strictly to the start of the taper region with the required gap
    taper_top.move((0, 0), (l_in, y_taper)) 

    # S-bend branching outward
    bend_top = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    bend_top.connect("o1", taper_top.ports["o2"])

    # Straight output parallel termination
    out_top = c << gf.components.straight(length=l_out, cross_section=xs)
    out_top.connect("o1", bend_top.ports["o2"])

    # --- 3. Bottom Waveguide ---
    # Mirrored bottom taper
    taper_bot = c << gf.components.taper(length=l_taper, width1=w_tip, width2=w_main)
    taper_bot.move((0, 0), (l_in, -y_taper)) 

    # S-bend branching outward (negative dy)
    bend_bot = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    bend_bot.connect("o1", taper_bot.ports["o2"])

    # Straight output parallel termination
    out_bot = c << gf.components.straight(length=l_out, cross_section=xs)
    out_bot.connect("o1", bend_bot.ports["o2"])

    return c

# Generate the component device and save the file
component = mode_converter_device()
component.write_gds("mode_converter.gds")