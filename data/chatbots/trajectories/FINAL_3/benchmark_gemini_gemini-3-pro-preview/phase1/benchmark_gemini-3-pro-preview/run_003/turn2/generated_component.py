import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    """
    Directional coupler with adjusted proportions to match the sharp transitions
    and long coupling region of the target image.
    
    Footprint: 120um x 4um
    Partitioning: 25um (Bend) - 70um (Straight) - 25um (Bend)
    """
    c = gf.Component()

    # --- Parameters ---
    # Total device constraints
    length_total = 120.0
    height_total = 4.0
    
    # Longitudinal partitioning
    # Increased straight length to match the visual "long coupling region" look.
    # Shortened bend length to create sharper S-bends.
    length_straight = 70.0
    length_bend = (length_total - length_straight) / 2  # 25.0 um
    
    # Cross-section specs
    wg_width = 0.5
    gap = 0.2
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Calculate Y-coordinates
    # Outer ports are aligned to the very edges of the 4um height
    y_top_outer = (height_total / 2) - (wg_width / 2)
    y_bot_outer = -(height_total / 2) + (wg_width / 2)
    
    # Inner ports are aligned to the central coupling gap
    y_top_inner = (gap / 2) + (wg_width / 2)
    y_bot_inner = -(gap / 2) - (wg_width / 2)
    
    # Vertical shift required for the S-bends
    dy = y_top_outer - y_top_inner

    # --- Geometry Construction ---

    # 1. Central Straight Coupling Region
    # Create two parallel straight waveguides
    wg_top = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_bot = c << gf.components.straight(length=length_straight, cross_section=xs)
    
    # Position them in the center (vertically) and offset by one bend length (horizontally)
    wg_top.move((length_bend, y_top_inner))
    wg_bot.move((length_bend, y_bot_inner))

    # 2. Input S-Bends (Left Side)
    # Top Left: Moves from Outer (High) to Inner (Low). Delta Y is negative.
    bend_in_top = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    # Connect the END of the bend (o2) to the START of the straight (o1)
    bend_in_top.connect("o2", wg_top.ports["o1"])
    
    # Bottom Left: Moves from Outer (Low) to Inner (High). Delta Y is positive.
    bend_in_bot = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_in_bot.connect("o2", wg_bot.ports["o1"])

    # 3. Output S-Bends (Right Side)
    # Top Right: Moves from Inner (Low) to Outer (High). Delta Y is positive.
    bend_out_top = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    # Connect the START of the bend (o1) to the END of the straight (o2)
    bend_out_top.connect("o1", wg_top.ports["o2"])
    
    # Bottom Right: Moves from Inner (High) to Outer (Low). Delta Y is negative.
    bend_out_bot = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_bot.ports["o2"])

    # --- Port Assignments ---
    c.add_port("o1", port=bend_in_bot.ports["o1"])
    c.add_port("o2", port=bend_in_top.ports["o1"])
    c.add_port("o3", port=bend_out_top.ports["o2"])
    c.add_port("o4", port=bend_out_bot.ports["o2"])

    return c

# Create and save the device
device = directional_coupler_refined()
device.write_gds("directional_coupler_refined.gds")