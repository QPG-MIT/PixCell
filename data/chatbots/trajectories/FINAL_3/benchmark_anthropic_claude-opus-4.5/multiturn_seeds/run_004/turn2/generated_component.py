import gdsfactory as gf

@gf.cell
def directional_coupler_2x2() -> gf.Component:
    """
    2x2 directional coupler with symmetric S-bend transitions.
    Two waveguides approach, run parallel in coupling region, then separate.
    
    Footprint: 120 µm x 4 µm
    """
    c = gf.Component()
    
    # Design parameters
    wg_width = 0.5
    coupling_gap = 0.2
    coupling_length = 50.0
    port_separation = 3.5
    sbend_length = 35.0
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Vertical positions
    y_port = port_separation / 2  # ±1.75 µm at input/output ports
    y_couple = (wg_width + coupling_gap) / 2  # ±0.35 µm in coupling region
    dy = y_port - y_couple  # 1.4 µm vertical offset for S-bends
    
    # ===== TOP ARM =====
    # Input S-bend: goes DOWN from y_port to y_couple
    s_in_top = c << gf.components.bend_s(size=(sbend_length, -dy), cross_section=xs)
    s_in_top.dmove((0, y_port))
    
    # Parallel coupling section
    wg_top = c << gf.components.straight(length=coupling_length, cross_section=xs)
    wg_top.connect("o1", s_in_top.ports["o2"])
    
    # Output S-bend: goes UP from y_couple to y_port
    s_out_top = c << gf.components.bend_s(size=(sbend_length, dy), cross_section=xs)
    s_out_top.connect("o1", wg_top.ports["o2"])
    
    # ===== BOTTOM ARM =====
    # Input S-bend: goes UP from -y_port to -y_couple
    s_in_bot = c << gf.components.bend_s(size=(sbend_length, dy), cross_section=xs)
    s_in_bot.dmove((0, -y_port))
    
    # Parallel coupling section
    wg_bot = c << gf.components.straight(length=coupling_length, cross_section=xs)
    wg_bot.connect("o1", s_in_bot.ports["o2"])
    
    # Output S-bend: goes DOWN from -y_couple to -y_port
    s_out_bot = c << gf.components.bend_s(size=(sbend_length, -dy), cross_section=xs)
    s_out_bot.connect("o1", wg_bot.ports["o2"])
    
    # ===== EXTERNAL PORTS =====
    c.add_port("o1", port=s_in_top.ports["o1"])
    c.add_port("o2", port=s_in_bot.ports["o1"])
    c.add_port("o3", port=s_out_top.ports["o2"])
    c.add_port("o4", port=s_out_bot.ports["o2"])
    
    return c


if __name__ == "__main__":
    device = directional_coupler_2x2()
    device.write_gds("directional_coupler_2x2.gds")