import gdsfactory as gf

@gf.cell
def smooth_directional_coupler() -> gf.Component:
    c = gf.Component("smooth_directional_coupler")
    
    # Define cross-section
    width = 0.5
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    
    # Calculate dimensions to meet the [18, 3] footprint exactly
    # Total height = 3.0. With width = 0.5, max Y = 1.5, min Y = -1.5
    # Centers of the input/output ports at the edges are at +/- 1.25
    y_start = 1.25
    
    # Central coupling region parameters
    gap = 0.2
    # The center Y coordinate of the top waveguide in the coupling region
    y_mid = gap / 2 + width / 2  # 0.1 + 0.25 = 0.35
    
    # S-bend vertical drop
    dy = y_start - y_mid  # 1.25 - 0.35 = 0.9
    
    # Lengths for the segments
    # Allocating 4 um for the central straight section to create the parallel coupling region
    coupling_length = 4.0
    dx = (18.0 - coupling_length) / 2.0  # (18 - 4) / 2 = 7.0 um for each S-bend
    
    # --- Top Arm ---
    s_top_left = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    str_top = c << gf.components.straight(length=coupling_length, cross_section=xs)
    s_top_right = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # Assemble top arm smoothly end-to-end
    s_top_left.movey(y_start)
    str_top.connect("o1", s_top_left.ports["o2"])
    s_top_right.connect("o1", str_top.ports["o2"])
    
    # --- Bottom Arm ---
    s_bot_left = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    str_bot = c << gf.components.straight(length=coupling_length, cross_section=xs)
    s_bot_right = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    
    # Assemble bottom arm smoothly end-to-end
    s_bot_left.movey(-y_start)
    str_bot.connect("o1", s_bot_left.ports["o2"])
    s_bot_right.connect("o1", str_bot.ports["o2"])
    
    # Add external ports for the overall component
    c.add_port("o1", port=s_top_left.ports["o1"])
    c.add_port("o2", port=s_bot_left.ports["o1"])
    c.add_port("o3", port=s_top_right.ports["o2"])
    c.add_port("o4", port=s_bot_right.ports["o2"])
    
    return c


if __name__ == "__main__":
    # Generate the component and save to GDS
    device = smooth_directional_coupler()
    device.write_gds("smooth_directional_coupler.gds")