import gdsfactory as gf

@gf.cell
def directional_coupler_refined_v3():
    """
    Directional coupler with a 120um x 4um footprint.
    Refined parameters to match visual proportions of the target:
    - Thinner waveguides (0.5um) for a cleaner look.
    - Ratio-matched coupling gap (0.25um).
    - Maximized vertical separation to fill the 4um height.
    - Dominant central coupling region.
    """
    c = gf.Component()

    # --- Constraints ---
    total_length = 120.0
    total_height = 4.0

    # --- Geometric Parameters ---
    wg_width = 0.5
    coupling_gap = 0.25
    
    # Longitudinal segmentation (Total = 120um)
    # Split: Straight_IO -> Bend -> Straight_Couple -> Bend -> Straight_IO
    # 10 + 25 + 50 + 25 + 10 = 120
    length_io = 10.0
    length_bend = 25.0
    length_couple = 50.0

    # --- Y-Axis Calculations ---
    # Outer ports: Centered to align outer edges with +/- 2.0um (Total height 4.0)
    # Center = (Total Height / 2) - (Waveguide Width / 2)
    y_io_top = (total_height / 2) - (wg_width / 2)       # 2.0 - 0.25 = 1.75
    y_io_bot = -y_io_top                                 # -1.75
    
    # Inner coupling: Centered around 0
    # Center = (Gap / 2) + (Waveguide Width / 2)
    y_couple_top = (coupling_gap / 2) + (wg_width / 2)   # 0.125 + 0.25 = 0.375
    y_couple_bot = -y_couple_top                         # -0.375
    
    # Vertical offset for the S-bends (dy)
    dy = y_io_top - y_couple_top                         # 1.75 - 0.375 = 1.375

    # Cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Component Definitions ---
    s_io = gf.components.straight(length=length_io, cross_section=xs)
    s_couple = gf.components.straight(length=length_couple, cross_section=xs)
    
    # S-Bends
    # Bend Down: Moves from Outer (High Y) to Inner (Low Y) -> negative dy
    bend_down = gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    # Bend Up: Moves from Inner (Low Y) to Outer (High Y) -> positive dy
    bend_up = gf.components.bend_s(size=(length_bend, dy), cross_section=xs)

    # --- Assembly (Left to Right) ---
    
    # -- Top Arm --
    # 1. Input Straight
    top_in = c << s_io
    top_in.move((0, y_io_top))
    
    # 2. Input Bend (Down towards coupling)
    top_bend_in = c << bend_down
    top_bend_in.connect("o1", top_in.ports["o2"])
    
    # 3. Coupling Straight
    top_mid = c << s_couple
    top_mid.connect("o1", top_bend_in.ports["o2"])
    
    # 4. Output Bend (Up away from coupling)
    top_bend_out = c << bend_up
    top_bend_out.connect("o1", top_mid.ports["o2"])
    
    # 5. Output Straight
    top_out = c << s_io
    top_out.connect("o1", top_bend_out.ports["o2"])

    # -- Bottom Arm --
    # 1. Input Straight
    bot_in = c << s_io
    bot_in.move((0, y_io_bot))
    
    # 2. Input Bend (Up towards coupling)
    bot_bend_in = c << bend_up
    bot_bend_in.connect("o1", bot_in.ports["o2"])
    
    # 3. Coupling Straight
    bot_mid = c << s_couple
    bot_mid.connect("o1", bot_bend_in.ports["o2"])
    
    # 4. Output Bend (Down away from coupling)
    bot_bend_out = c << bend_down
    bot_bend_out.connect("o1", bot_mid.ports["o2"])
    
    # 5. Output Straight
    bot_out = c << s_io
    bot_out.connect("o1", bot_bend_out.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=bot_in.ports["o1"])
    c.add_port("o2", port=top_in.ports["o1"])
    c.add_port("o3", port=top_out.ports["o2"])
    c.add_port("o4", port=bot_out.ports["o2"])

    return c

# Generate and save
device = directional_coupler_refined_v3()
device.write_gds("directional_coupler_refined_v3.gds")