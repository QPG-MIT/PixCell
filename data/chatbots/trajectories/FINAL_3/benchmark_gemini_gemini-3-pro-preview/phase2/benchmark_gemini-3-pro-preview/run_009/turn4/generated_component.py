import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Creates a directional coupler matching the 120um x 4um footprint.
    
    Design Breakdown:
    - Total Footprint: 120um (Length) x 4um (Height)
    - Architecture: Input Straights -> S-Bends -> Central Parallel Coupler -> S-Bends -> Output Straights
    - Dimensions:
      - Waveguide Width: 0.5um
      - Coupling Gap: 0.2um (Visual estimation and standard high-coupling gap)
      - Vertical IO Separation: 3.5um center-to-center (fits within 4um height with 0.5um width)
      - Longitudinal Segmentation: 10um (Straight) + 20um (Bend) + 60um (Coupler) + 20um (Bend) + 10um (Straight)
    
    Improvements:
    - Replaced `coupler_straight` with explicit manual placement of parallel waveguides for robust port handling.
    - Simplified geometry construction to ensure symmetry and exact dimension compliance.
    """
    c = gf.Component()
    
    # === Parameters ===
    # Geometric Constraints
    total_length = 120.0
    total_height = 4.0
    
    wg_width = 0.5
    gap = 0.2
    
    # Longitudinal Sections
    l_coupling = 60.0
    l_bend = 20.0
    l_straight = (total_length - l_coupling - 2 * l_bend) / 2  # 10.0 um
    
    # Vertical Positions (Center-to-Center)
    # IO ports at the vertical limits (edge at +/- 2.0um)
    # Center = 2.0 - 0.5/2 = 1.75
    y_io_top = (total_height - wg_width) / 2
    y_io_bot = -y_io_top
    
    # Coupling Region
    # Gap 0.2um -> Center spacing = 0.5 + 0.2 = 0.7 -> +/- 0.35
    y_coup_top = (gap + wg_width) / 2
    y_coup_bot = -y_coup_top
    
    # Bend Offset
    dy = y_io_top - y_coup_top  # 1.4 um

    # Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # === Component Assembly ===
    
    # 1. Central Coupling Region
    # Manually placing two straight waveguides ensures we know exactly where ports are
    # and avoids ambiguity in `coupler_straight` port mapping.
    coup_top = c << gf.components.straight(length=l_coupling, cross_section=xs)
    coup_bot = c << gf.components.straight(length=l_coupling, cross_section=xs)
    
    # Center the coupling region at (0,0)
    coup_top.x = 0
    coup_top.y = y_coup_top
    coup_bot.x = 0
    coup_bot.y = y_coup_bot

    # 2. Primitives for Input/Output
    # S-bends for transitions
    # bend_s definition: size=(x_length, y_offset)
    s_bend_down = gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    s_bend_up = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    
    # Straight sections for IO
    io_straight = gf.components.straight(length=l_straight, cross_section=xs)

    # 3. Connections
    # We build outwards from the central coupler to ensure perfect alignment.
    
    # --- West Side (Inputs) ---
    # Top Input Path: Straight -> Bend Down -> Coupler Top (West Port)
    
    # Place Bend: Connect its END ("o2") to the Coupler's INPUT ("o1")
    # Note: coup_top "o1" is the West port.
    bw_top = c << s_bend_down
    bw_top.connect("o2", coup_top.ports["o1"])
    
    # Place Straight: Connect its END ("o2") to the Bend's START ("o1")
    sw_top = c << io_straight
    sw_top.connect("o2", bw_top.ports["o1"])
    
    # Bottom Input Path
    bw_bot = c << s_bend_up
    bw_bot.connect("o2", coup_bot.ports["o1"])
    
    sw_bot = c << io_straight
    sw_bot.connect("o2", bw_bot.ports["o1"])
    
    # --- East Side (Outputs) ---
    # Top Output Path: Coupler Top (East Port) -> Bend Up -> Straight
    
    # Place Bend: Connect its START ("o1") to the Coupler's OUTPUT ("o2")
    be_top = c << s_bend_up
    be_top.connect("o1", coup_top.ports["o2"])
    
    # Place Straight: Connect its START ("o1") to the Bend's END ("o2")
    se_top = c << io_straight
    se_top.connect("o1", be_top.ports["o2"])
    
    # Bottom Output Path
    be_bot = c << s_bend_down
    be_bot.connect("o1", coup_bot.ports["o2"])
    
    se_bot = c << io_straight
    se_bot.connect("o1", be_bot.ports["o2"])

    # === 4. Expose Ports ===
    # Map component ports to the top-level cell
    c.add_port("o1", port=sw_top.ports["o1"])  # Input Top
    c.add_port("o2", port=sw_bot.ports["o1"])  # Input Bot
    c.add_port("o3", port=se_top.ports["o2"])  # Output Top
    c.add_port("o4", port=se_bot.ports["o2"])  # Output Bot
    
    return c

if __name__ == "__main__":
    # Generate and save the GDS
    device = directional_coupler_120x4()
    device.write_gds("directional_coupler_120x4.gds")