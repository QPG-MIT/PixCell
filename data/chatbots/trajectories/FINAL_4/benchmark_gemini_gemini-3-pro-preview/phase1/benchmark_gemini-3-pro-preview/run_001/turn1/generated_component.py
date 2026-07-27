import gdsfactory as gf

@gf.cell
def directional_coupler_18x3():
    c = gf.Component()

    # =============================================================
    # Parameters derived from footprint 18um x 3um
    # =============================================================
    length_straight = 4.0       # Length of the central coupling region
    length_bend = 7.0           # Length of the input/output S-bends
    gap = 0.2                   # Gap between waveguides in the center
    width = 0.5                 # Waveguide width
    dy = 0.9                    # Vertical displacement of the S-bends
    
    # Create Cross Section
    xs = gf.cross_section.cross_section(width=width)

    # =============================================================
    # 1. Central Straight Region
    # =============================================================
    # Create two parallel straight waveguides for the coupling region
    # Top straight
    wg_top = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_top.movey((gap + width) / 2)
    
    # Bottom straight
    wg_bot = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_bot.movey(-(gap + width) / 2)

    # =============================================================
    # 2. Input S-Bends (Left Side)
    # =============================================================
    # Top Left: Connects to straight input (o1). Needs to come from higher Y.
    # bend_s(size=(x, y)) goes from 0 to y. Connecting "o2" to straight means 
    # the start (o1) is at -y relative to straight. We want +dy relative offset.
    # Therefore y = -dy.
    sb_in_top = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    sb_in_top.connect("o2", wg_top.ports["o1"])

    # Bottom Left: Connects to straight input. Needs to come from lower Y.
    # We want start (o1) at -dy relative to straight. 
    # Therefore y = dy.
    sb_in_bot = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    sb_in_bot.connect("o2", wg_bot.ports["o1"])

    # =============================================================
    # 3. Output S-Bends (Right Side)
    # =============================================================
    # Top Right: Connects to straight output (o2). Needs to go to higher Y.
    # We want end (o2) at +dy relative to straight.
    # Therefore y = dy.
    sb_out_top = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    sb_out_top.connect("o1", wg_top.ports["o2"])

    # Bottom Right: Connects to straight output. Needs to go to lower Y.
    # We want end (o2) at -dy relative to straight.
    # Therefore y = -dy.
    sb_out_bot = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    sb_out_bot.connect("o1", wg_bot.ports["o2"])

    # =============================================================
    # 4. Expose Ports
    # =============================================================
    c.add_port("o1", port=sb_in_top.ports["o1"]) # Top Input
    c.add_port("o2", port=sb_in_bot.ports["o1"]) # Bottom Input
    c.add_port("o3", port=sb_out_top.ports["o2"]) # Top Output
    c.add_port("o4", port=sb_out_bot.ports["o2"]) # Bottom Output

    return c

# Create and save the device
device = directional_coupler_18x3()
device.write_gds("directional_coupler_18x3.gds")