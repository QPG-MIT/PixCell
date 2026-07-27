import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Creates a directional coupler with a 4um x 240um footprint.
    Constructed using straight waveguides and S-bends.
    """
    c = gf.Component()

    # 1. Define Parameters based on footprint constraints
    # Total length = 240um
    # Total height = 4um
    
    wg_width = 0.5
    
    # Y-axis calculations:
    # To fit exactly in 4um height centered at y=0:
    # Top edge = 2.0, Bottom edge = -2.0.
    # Center of input waveguide = 2.0 - (wg_width / 2) = 1.75
    y_input_offset = 1.75 
    
    # Coupling region calculations:
    # Assume a standard 200nm (0.2um) gap for the directional coupler.
    gap = 0.2
    # Center of coupling waveguide = 0 (midpoint) + gap/2 + wg_width/2
    y_couple_offset = (gap + wg_width) / 2  # 0.35 um
    
    # X-axis calculations:
    # Total 240um split into: Bend + Straight + Bend
    l_bend = 40.0
    l_coupler = 240.0 - (2 * l_bend) # 160.0 um
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # ==========================================================
    # 2. Build Central Coupling Region (Straight Parts)
    # ==========================================================
    
    # Create the two straight parallel waveguides
    coupler_top = c << gf.components.straight(length=l_coupler, cross_section=xs)
    coupler_bot = c << gf.components.straight(length=l_coupler, cross_section=xs)

    # Move them to the coupling Y positions
    coupler_top.movey(y_couple_offset)
    coupler_bot.movey(-y_couple_offset)
    
    # Move them in X to start after the first bend
    coupler_top.movex(l_bend)
    coupler_bot.movex(l_bend)

    # ==========================================================
    # 3. Build Input S-Bends (Left Side)
    # ==========================================================
    
    # Calculate vertical shift required (dy)
    # Top: From y=1.75 (Input) down to y=0.35 (Coupler) -> dy = -1.4
    dy = y_input_offset - y_couple_offset
    
    # Top Input Bend
    # bend_s size is (length, height_change).
    # We create the bend and connect its END (o2) to the coupler START (o1).
    sbend_in_top = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    sbend_in_top.connect("o2", coupler_top.ports["o1"])
    
    # Bottom Input Bend
    # From y=-1.75 up to y=-0.35 -> dy = +1.4
    sbend_in_bot = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    sbend_in_bot.connect("o2", coupler_bot.ports["o1"])

    # ==========================================================
    # 4. Build Output S-Bends (Right Side)
    # ==========================================================
    
    # Top Output Bend
    # From y=0.35 (Coupler) up to y=1.75 (Output) -> dy = +1.4
    # Connect its START (o1) to the coupler END (o2).
    sbend_out_top = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    sbend_out_top.connect("o1", coupler_top.ports["o2"])
    
    # Bottom Output Bend
    # From y=-0.35 down to y=-1.75 -> dy = -1.4
    sbend_out_bot = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    sbend_out_bot.connect("o1", coupler_bot.ports["o2"])

    # ==========================================================
    # 5. Expose Ports
    # ==========================================================
    c.add_port("o1", port=sbend_in_bot.ports["o1"])  # Input Bottom
    c.add_port("o2", port=sbend_in_top.ports["o1"])  # Input Top
    c.add_port("o3", port=sbend_out_top.ports["o2"]) # Output Top
    c.add_port("o4", port=sbend_out_bot.ports["o2"]) # Output Bottom

    return c

if __name__ == "__main__":
    device = directional_coupler_4x240()
    device.write_gds("directional_coupler.gds")
    print("GDS Generated: directional_coupler.gds")