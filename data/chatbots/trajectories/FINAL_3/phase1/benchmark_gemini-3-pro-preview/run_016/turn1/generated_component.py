import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Creates a Directional Coupler with 4um x 240um footprint.
    Based on image analysis:
    - Central parallel coupling region.
    - 4 S-bends for input/output transitions.
    """
    c = gf.Component()
    
    # --- 1. Define Parameters ---
    # Constraints
    total_length = 240.0
    total_height = 4.0
    
    # Standard silicon photonics dimensions (estimated)
    wg_width = 0.5
    gap = 0.2
    
    # Geometry Partitioning:
    # We allocate length to the central coupler and the bends.
    # 140um straight + 50um bend + 50um bend = 240um total.
    coupling_length = 140.0
    bend_length = (total_length - coupling_length) / 2
    
    # Vertical Offset Calculation:
    # 4um footprint = Outer-edge to Outer-edge distance.
    # Y-center of Top Input Port = (Height/2) - (Width/2) = 2.0 - 0.25 = 1.75
    # Y-center of Top Coupler Arm = (Gap/2) + (Width/2) = 0.1 + 0.25 = 0.35
    # The vertical shift (dy) required for the S-bend:
    dy = 1.75 - 0.35  # 1.4 um

    xs = gf.cross_section.strip(width=wg_width)

    # --- 2. Central Coupler ---
    # Creates two parallel straights centered at (0,0)
    # Ports: o1 (top left), o2 (bot left), o3 (top right), o4 (bot right)
    coupler_core = c << gf.components.coupler_straight(
        length=coupling_length,
        gap=gap,
        cross_section=xs
    )

    # --- 3. Input Bends (Left Side) ---
    # Top Left: Needs to slope DOWN from input (left) to coupler (right).
    # bend_s defaults to sloping UP, so we mirror it vertically.
    sb_in_top = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs)
    sb_in_top.mirror_y()
    # Connect right side of bend (o2) to left side of coupler (o1)
    sb_in_top.connect("o2", coupler_core.ports["o1"])

    # Bottom Left: Needs to slope UP from input (left) to coupler (right).
    sb_in_bot = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs)
    sb_in_bot.connect("o2", coupler_core.ports["o2"])

    # --- 4. Output Bends (Right Side) ---
    # Top Right: Needs to slope UP from coupler (left) to output (right).
    sb_out_top = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs)
    sb_out_top.connect("o1", coupler_core.ports["o3"])

    # Bottom Right: Needs to slope DOWN from coupler (left) to output (right).
    sb_out_bot = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs)
    sb_out_bot.mirror_y()
    sb_out_bot.connect("o1", coupler_core.ports["o4"])

    # --- 5. Expose Ports ---
    # Map internal bend ports to the main component ports
    c.add_port("o1", port=sb_in_top.ports["o1"])
    c.add_port("o2", port=sb_in_bot.ports["o1"])
    c.add_port("o3", port=sb_out_top.ports["o2"])
    c.add_port("o4", port=sb_out_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Instantiate the component
    dc = directional_coupler_4x240()
    
    # Define output filename
    output_gds = "directional_coupler_4x240.gds"
    
    # Write GDS file
    dc.write_gds(output_gds)
    
    print(f"Success! GDS file written to: {output_gds}")