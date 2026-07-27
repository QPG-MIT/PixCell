import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Creates a directional coupler matching the 120um x 4um footprint.
    Correction:
    - Fixed port access to avoid AttributeError (using dictionary keys/direct access).
    - Implemented geometric sorting of ports to prevent waveguide crossing.
    - Added straight input/output sections to match target profile.
    """
    c = gf.Component()
    
    # === Parameters ===
    # Footprint constraints
    total_length = 120.0
    total_height = 4.0
    
    # Waveguide parameters
    wg_width = 0.5
    gap = 0.2
    
    # Longitudinal Segmentation
    # Total 120um = Straight(10) + Bend(20) + Coupling(60) + Bend(20) + Straight(10)
    l_coupling = 60.0
    l_bend = 20.0
    l_straight = (total_length - l_coupling - 2 * l_bend) / 2 # 10.0 um
    
    # Vertical Dimensions
    # IO Port Y positions (centered)
    y_io_top = (total_height - wg_width) / 2   # 1.75
    y_io_bot = -y_io_top                       # -1.75
    
    # Coupler Y positions (calculated from gap)
    y_coup_top = (gap + wg_width) / 2          # 0.35
    y_coup_bot = -y_coup_top                   # -0.35
    
    # Vertical shift for S-bends
    # Top path: 1.75 -> 0.35 (Drop 1.4)
    dy = y_io_top - y_coup_top # 1.4 um

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # === Component Creation ===
    
    # 1. Central Coupling Region
    coupler_core = c << gf.components.coupler_straight(
        length=l_coupling,
        gap=gap,
        cross_section=xs
    )
    
    # 2. Robust Port Identification
    # Retrieve ports by name explicitly to avoid .values() error on DInstancePorts
    # We expect o1, o2 (West) and o3, o4 (East) from coupler_straight
    p_w1 = coupler_core.ports['o1']
    p_w2 = coupler_core.ports['o2']
    p_e1 = coupler_core.ports['o3']
    p_e2 = coupler_core.ports['o4']
    
    # Sort West ports by Y to identify Top/Bottom
    if p_w1.center[1] > p_w2.center[1]:
        w_top = p_w1
        w_bot = p_w2
    else:
        w_top = p_w2
        w_bot = p_w1

    # Sort East ports by Y
    if p_e1.center[1] > p_e2.center[1]:
        e_top = p_e1
        e_bot = p_e2
    else:
        e_top = p_e2
        e_bot = p_e1

    # 3. Define Primitives
    # Straight section
    wg_straight = gf.components.straight(length=l_straight, cross_section=xs)
    
    # Bend Down (for Top Input -> Coupler, and Coupler -> Bot Output)
    # Starts at (0,0), ends at (L, -dy)
    bend_down = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    
    # Bend Up (for Bot Input -> Coupler, and Coupler -> Top Output)
    # Starts at (0,0), ends at (L, dy)
    bend_up = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    
    # === 4. Assembly ===
    
    # --- Input Side (West) ---
    
    # Top Input Path: Straight -> Bend Down -> Coupler Top (w_top)
    # Place Bend
    in_top_bend = c << bend_down
    in_top_bend.connect("o2", w_top) # Connect end of bend to coupler
    
    # Place Straight
    in_top_str = c << wg_straight
    in_top_str.connect("o2", in_top_bend.ports["o1"]) # Connect end of straight to start of bend
    
    # Bottom Input Path: Straight -> Bend Up -> Coupler Bot (w_bot)
    in_bot_bend = c << bend_up
    in_bot_bend.connect("o2", w_bot)
    
    in_bot_str = c << wg_straight
    in_bot_str.connect("o2", in_bot_bend.ports["o1"])
    
    # --- Output Side (East) ---
    
    # Top Output Path: Coupler Top (e_top) -> Bend Up -> Straight
    # Place Bend
    out_top_bend = c << bend_up
    out_top_bend.connect("o1", e_top) # Connect start of bend to coupler
    
    # Place Straight
    out_top_str = c << wg_straight
    out_top_str.connect("o1", out_top_bend.ports["o2"]) # Connect start of straight to end of bend
    
    # Bottom Output Path: Coupler Bot (e_bot) -> Bend Down -> Straight
    out_bot_bend = c << bend_down
    out_bot_bend.connect("o1", e_bot)
    
    out_bot_str = c << wg_straight
    out_bot_str.connect("o1", out_bot_bend.ports["o2"])
    
    # === 5. Add Ports ===
    c.add_port("o1", port=in_top_str.ports["o1"]) # Top Input
    c.add_port("o2", port=in_bot_str.ports["o1"]) # Bot Input
    c.add_port("o3", port=out_top_str.ports["o2"]) # Top Output
    c.add_port("o4", port=out_bot_str.ports["o2"]) # Bot Output
    
    return c

# Generate and save
device = directional_coupler_120x4()
device.write_gds("directional_coupler_120x4.gds")