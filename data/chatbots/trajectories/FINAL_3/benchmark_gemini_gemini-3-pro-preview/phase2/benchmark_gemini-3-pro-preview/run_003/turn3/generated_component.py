import gdsfactory as gf

@gf.cell
def directional_coupler_refined_v2():
    """
    Directional coupler with adjusted proportions to match the target image.
    
    Refinements:
    - Reduced straight coupling length from 70um to 50um to match visual ratio.
    - Increased bend length from 25um to 35um for smoother, longer transitions.
    - Increased waveguide width to 0.6um to match the visual line weight/gap ratio.
    
    Footprint: 120um x 4um
    Partitioning: 35um (Bend) - 50um (Straight) - 35um (Bend)
    """
    c = gf.Component()

    # --- Parameters ---
    # Total device constraints
    length_total = 120.0
    height_total = 4.0
    
    # Longitudinal partitioning
    # Visual estimation from target: Straight section is approx 40-45% of total.
    length_straight = 50.0
    length_bend = (length_total - length_straight) / 2  # 35.0 um
    
    # Cross-section specs
    # Width increased to 0.6 to match the visual thickness relative to the gap.
    wg_width = 0.6
    gap = 0.2
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Calculate Y-coordinates
    # Outer ports are aligned to the very edges of the 4um height constraint
    y_top_outer = (height_total / 2) - (wg_width / 2)
    y_bot_outer = -(height_total / 2) + (wg_width / 2)
    
    # Inner ports are aligned to the central coupling gap
    y_top_inner = (gap / 2) + (wg_width / 2)
    y_bot_inner = -(gap / 2) - (wg_width / 2)
    
    # Vertical shift required for the S-bends
    dy = y_top_outer - y_top_inner

    # --- Geometry Construction ---

    # 1. Central Straight Coupling Region
    wg_top = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_bot = c << gf.components.straight(length=length_straight, cross_section=xs)
    
    # Position them in the center (vertically) and offset by one bend length (horizontally)
    wg_top.move((length_bend, y_top_inner))
    wg_bot.move((length_bend, y_bot_inner))

    # 2. Input S-Bends (Left Side)
    # Top Left: Outer (High) -> Inner (Low). Delta Y is negative.
    bend_in_top = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_in_top.connect("o2", wg_top.ports["o1"])
    
    # Bottom Left: Outer (Low) -> Inner (High). Delta Y is positive.
    bend_in_bot = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_in_bot.connect("o2", wg_bot.ports["o1"])

    # 3. Output S-Bends (Right Side)
    # Top Right: Inner (Low) -> Outer (High). Delta Y is positive.
    bend_out_top = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_out_top.connect("o1", wg_top.ports["o2"])
    
    # Bottom Right: Inner (High) -> Outer (Low). Delta Y is negative.
    bend_out_bot = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_bot.ports["o2"])

    # --- Port Assignments ---
    c.add_port("o1", port=bend_in_bot.ports["o1"])
    c.add_port("o2", port=bend_in_top.ports["o1"])
    c.add_port("o3", port=bend_out_top.ports["o2"])
    c.add_port("o4", port=bend_out_bot.ports["o2"])

    return c

# Create and save the device
device = directional_coupler_refined_v2()
device.write_gds("directional_coupler_refined_v2.gds")