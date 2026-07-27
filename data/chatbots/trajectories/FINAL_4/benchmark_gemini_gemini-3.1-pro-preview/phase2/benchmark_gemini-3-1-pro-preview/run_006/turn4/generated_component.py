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
    # The center Y coordinate of the top waveguide at its closest point to the center
    y_mid = gap / 2 + width / 2  # 0.1 + 0.25 = 0.35
    
    # S-bend vertical drop required to get from the port to the coupling region
    dy = y_start - y_mid  # 1.25 - 0.35 = 0.9
    
    # To remove the straight section and match the continuous curve, 
    # we devote the entire 18um length to the S-bends
    dx = 18.0 / 2.0  # 9.0 um for each half of the curve
    
    # --- Top Arm ---
    # First half S-bend curving downwards
    s_top_left = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    # Second half S-bend curving upwards to return to the original height
    s_top_right = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # Assemble top arm smoothly end-to-end
    s_top_left.movey(y_start)
    s_top_right.connect("o1", s_top_left.ports["o2"])
    
    # --- Bottom Arm ---
    # First half S-bend curving upwards
    s_bot_left = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    # Second half S-bend curving downwards
    s_bot_right = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    
    # Assemble bottom arm smoothly end-to-end
    s_bot_left.movey(-y_start)
    s_bot_right.connect("o1", s_bot_left.ports["o2"])
    
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