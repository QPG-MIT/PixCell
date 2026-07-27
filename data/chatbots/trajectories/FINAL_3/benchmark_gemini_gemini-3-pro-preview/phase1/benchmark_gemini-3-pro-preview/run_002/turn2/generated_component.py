import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Creates a directional coupler with a 120um x 4um footprint.
    Parameters are tuned to match the visual proportions of the reference image:
    - Thicker waveguides (0.8um) to match the visual weight of the lines.
    - Shorter straight section (40um) to allow for longer, smoother S-bends.
    - Tight gap (0.2um).
    """
    c = gf.Component()

    # --- Design Parameters ---
    total_length = 120.0
    total_height = 4.0
    
    # Geometry tuning based on visual reference
    wg_width = 0.8   # Increased width to match image line thickness
    gap = 0.2        # Narrow gap
    
    # Longitudinal partition
    # The reference shows a shorter straight section relative to the bends
    length_straight = 40.0 
    length_sbend = (total_length - length_straight) / 2  # 40.0 um per side
    
    # Vertical Positions Calculation
    # 1. Coupling Region: Center-to-center distance
    # Center y = gap/2 + width/2
    y_couple_offset = (gap + wg_width) / 2
    
    # 2. Input/Output Ports: Center-to-center distance
    # To meet 4.0um total height, outer edge is at y=2.0
    # Center y = 2.0 - width/2
    y_port_offset = (total_height / 2) - (wg_width / 2)
    
    # Vertical shift required for S-bends
    dy = y_port_offset - y_couple_offset
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width)

    # --- Component Construction ---

    # 1. Central Coupling Region (Two parallel straights)
    wg_top_mid = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_top_mid.movey(y_couple_offset)
    
    wg_bot_mid = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_bot_mid.movey(-y_couple_offset)
    
    # 2. Input S-Bends (Connect ports to center)
    # Top Input: Starts high, bends down to coupling region
    sb_in_top = c << gf.components.bend_s(size=(length_sbend, -dy), cross_section=xs)
    sb_in_top.connect("o2", wg_top_mid.ports["o1"])
    
    # Bottom Input: Starts low, bends up to coupling region
    sb_in_bot = c << gf.components.bend_s(size=(length_sbend, dy), cross_section=xs)
    sb_in_bot.connect("o2", wg_bot_mid.ports["o1"])
    
    # 3. Output S-Bends (Connect center to ports)
    # Top Output: Starts at coupling region, bends up
    sb_out_top = c << gf.components.bend_s(size=(length_sbend, dy), cross_section=xs)
    sb_out_top.connect("o1", wg_top_mid.ports["o2"])
    
    # Bottom Output: Starts at coupling region, bends down
    sb_out_bot = c << gf.components.bend_s(size=(length_sbend, -dy), cross_section=xs)
    sb_out_bot.connect("o1", wg_bot_mid.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=sb_in_bot.ports["o1"])
    c.add_port("o2", port=sb_in_top.ports["o1"])
    c.add_port("o3", port=sb_out_top.ports["o2"])
    c.add_port("o4", port=sb_out_bot.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler_120x4()
    device.write_gds("directional_coupler_120x4.gds")
    device.show()