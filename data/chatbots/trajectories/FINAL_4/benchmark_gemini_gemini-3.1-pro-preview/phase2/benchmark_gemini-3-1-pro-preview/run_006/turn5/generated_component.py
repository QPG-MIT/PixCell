import gdsfactory as gf

@gf.cell
def smooth_directional_coupler() -> gf.Component:
    c = gf.Component("smooth_directional_coupler")
    
    # Define cross-section and explicitly set a small radius_min 
    # to bypass the default 10.0um validation limit for tight S-bends.
    width = 0.5
    layer = (1, 0)
    xs = gf.cross_section.cross_section(
        width=width, 
        layer=layer, 
        radius=2.0,      # Smaller default radius
        radius_min=1.0   # Explicitly allow tight bend radii
    )
    
    # Calculate dimensions to meet the [18, 3] footprint exactly
    # Total height = 3.0. With width = 0.5, max Y = 1.5, min Y = -1.5
    # Centers of the input/output ports at the edges are at +/- 1.25
    y_port = 1.25
    
    # Central coupling region parameters
    gap = 0.2
    # The center Y coordinate of the top waveguide at its closest point to the center
    y_mid = gap / 2 + width / 2  # 0.1 + 0.25 = 0.35
    
    # S-bend vertical drop required to get from the port to the coupling region
    dy = y_port - y_mid  # 1.25 - 0.35 = 0.9
    
    # Distribute the 18um total length into S-bends and a central straight section.
    # A 4um straight section and 7um S-bends closely matches the proportions of the target image.
    L_total = 18.0
    L_straight = 4.0
    L_sbend = (L_total - L_straight) / 2.0  # 7.0
    
    # Pre-generate primitives to use in both arms
    sbend_down = gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    sbend_up = gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    straight = gf.components.straight(length=L_straight, cross_section=xs)
    
    # --- Top Arm ---
    # S-bend curving downwards
    top_left = c << sbend_down
    # Straight coupling section
    top_straight = c << straight
    # S-bend curving upwards to return to the original height
    top_right = c << sbend_up
    
    # Assemble top arm smoothly end-to-end
    top_left.movey(y_port)
    top_straight.connect("o1", top_left.ports["o2"])
    top_right.connect("o1", top_straight.ports["o2"])
    
    # --- Bottom Arm ---
    # S-bend curving upwards
    bot_left = c << sbend_up
    # Straight coupling section
    bot_straight = c << straight
    # S-bend curving downwards
    bot_right = c << sbend_down
    
    # Assemble bottom arm smoothly end-to-end
    bot_left.movey(-y_port)
    bot_straight.connect("o1", bot_left.ports["o2"])
    bot_right.connect("o1", bot_straight.ports["o2"])
    
    # Add external ports for the overall component
    c.add_port("o1", port=top_left.ports["o1"])
    c.add_port("o2", port=bot_left.ports["o1"])
    c.add_port("o3", port=top_right.ports["o2"])
    c.add_port("o4", port=bot_right.ports["o2"])
    
    return c


if __name__ == "__main__":
    # Generate the component and save to GDS
    device = smooth_directional_coupler()
    device.write_gds("smooth_directional_coupler.gds")