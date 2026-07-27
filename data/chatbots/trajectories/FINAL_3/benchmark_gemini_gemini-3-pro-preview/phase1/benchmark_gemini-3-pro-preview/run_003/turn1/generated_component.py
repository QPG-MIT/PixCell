import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Creates a directional coupler matching the 120um x 4um footprint.
    Constructed using straight and bend_s primitives.
    """
    c = gf.Component()
    
    # --- Parameters ---
    # Constraints
    length_total = 120.0
    height_total = 4.0
    
    # Waveguide specs
    wg_width = 0.5
    gap = 0.2
    
    # Longitudinal partitioning
    # The device is symmetric. We estimate the coupling length is roughly 1/3 of total.
    length_straight = 40.0
    length_bend = (length_total - length_straight) / 2  # 40.0 um
    
    # Vertical partitioning
    # Calculate y-coordinates to satisfy the 4um total height constraint
    # Outer ports are at the very edges of the 4um box
    y_top_outer = (height_total / 2) - (wg_width / 2)
    y_bot_outer = -(height_total / 2) + (wg_width / 2)
    
    # Inner ports (coupling region) are centered around y=0
    y_top_inner = (gap / 2) + (wg_width / 2)
    y_bot_inner = -(gap / 2) - (wg_width / 2)
    
    # Calculate the vertical shift (dy) required for the S-bends
    dy = y_top_outer - y_top_inner
    
    # Cross-section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Geometry Construction ---

    # 1. Central Coupling Region
    # We construct this from two straight waveguides to ensure precise port control
    wg_straight_top = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_straight_bot = c << gf.components.straight(length=length_straight, cross_section=xs)
    
    # Position the straights
    wg_straight_top.movey(y_top_inner)
    wg_straight_bot.movey(y_bot_inner)

    # 2. Input S-Bends (Left Side)
    # Top Left: Bends "down" from outer to inner. dy is negative.
    bend_in_top = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    # Connect the END of the bend (o2) to the START of the straight (o1)
    bend_in_top.connect("o2", wg_straight_top.ports["o1"])
    
    # Bottom Left: Bends "up" from outer to inner. dy is positive.
    bend_in_bot = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_in_bot.connect("o2", wg_straight_bot.ports["o1"])

    # 3. Output S-Bends (Right Side)
    # Top Right: Bends "up" from inner to outer. dy is positive.
    bend_out_top = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    # Connect the START of the bend (o1) to the END of the straight (o2)
    bend_out_top.connect("o1", wg_straight_top.ports["o2"])
    
    # Bottom Right: Bends "down" from inner to outer. dy is negative.
    bend_out_bot = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_straight_bot.ports["o2"])

    # --- Port Assignments ---
    c.add_port("o1", port=bend_in_bot.ports["o1"]) # Bottom Left Input
    c.add_port("o2", port=bend_in_top.ports["o1"]) # Top Left Input
    c.add_port("o3", port=bend_out_top.ports["o2"]) # Top Right Output
    c.add_port("o4", port=bend_out_bot.ports["o2"]) # Bottom Right Output

    return c

# Create and save the device
device = directional_coupler_120x4()
device.write_gds("directional_coupler_120x4.gds")