import gdsfactory as gf

@gf.cell
def coupler_4x240():
    """
    Recreates the directional coupler from the image.
    Constraint: 4um x 240um footprint.
    """
    c = gf.Component()

    # --- 1. Define Geometry Constraints ---
    total_length = 240.0
    total_height = 4.0
    
    # Waveguide parameters
    wg_width = 0.5
    gap = 0.2
    
    # --- 2. Calculate Derived Dimensions ---
    
    # Vertical Positions (Y-axis)
    # The footprint is 4um high (from y=-2.0 to y=+2.0).
    # The waveguide centers at the input/output ports are determined by the outer edges.
    y_top_port = (total_height / 2) - (wg_width / 2)   # 2.0 - 0.25 = 1.75
    y_bot_port = -y_top_port                           # -1.75
    
    # The waveguide centers in the coupling region (middle) are determined by the gap.
    y_top_couple = (gap + wg_width) / 2                # 0.1 + 0.25 = 0.35
    y_bot_couple = -y_top_couple                       # -0.35
    
    # Vertical shift required for the S-bends
    dy = y_top_port - y_top_couple                     # 1.75 - 0.35 = 1.4

    # Horizontal Lengths (X-axis)
    # Total length is 240um. We split this into input bends, straight coupler, output bends.
    # We assign 100um to the straight coupling region and the rest to bends.
    length_straight = 100.0
    length_bend = (total_length - length_straight) / 2 # (240 - 100)/2 = 70.0

    # Cross section definition
    xs = gf.cross_section.cross_section(width=wg_width)

    # --- 3. Instantiate Primitives ---

    # Central Coupling Region (Straight Waveguides)
    wg_straight_top = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_straight_bot = c << gf.components.straight(length=length_straight, cross_section=xs)

    # Move straights to their calculated vertical coupling positions
    wg_straight_top.movey(y_top_couple)
    wg_straight_bot.movey(y_bot_couple)

    # Input S-Bends (Left Side)
    # Top Left: Bends DOWN from port to coupler. Size=(L, -dy)
    bend_in_top = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    # Bottom Left: Bends UP from port to coupler. Size=(L, +dy)
    bend_in_bot = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)

    # Output S-Bends (Right Side)
    # Top Right: Bends UP from coupler to port. Size=(L, +dy)
    bend_out_top = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    # Bottom Right: Bends DOWN from coupler to port. Size=(L, -dy)
    bend_out_bot = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)

    # --- 4. Connect Components ---

    # Connect Input Bends -> Straights
    bend_in_top.connect("o2", wg_straight_top.ports["o1"])
    bend_in_bot.connect("o2", wg_straight_bot.ports["o1"])

    # Connect Straights -> Output Bends
    bend_out_top.connect("o1", wg_straight_top.ports["o2"])
    bend_out_bot.connect("o1", wg_straight_bot.ports["o2"])

    # --- 5. Expose Ports ---
    c.add_port("o1", port=bend_in_top.ports["o1"])  # Top Left
    c.add_port("o2", port=bend_in_bot.ports["o1"])  # Bottom Left
    c.add_port("o3", port=bend_out_top.ports["o2"]) # Top Right
    c.add_port("o4", port=bend_out_bot.ports["o2"]) # Bottom Right

    return c

# --- Execution ---
if __name__ == "__main__":
    # Create the component
    device = coupler_4x240()
    
    # Save to GDS file
    gds_filename = "coupler_4x240.gds"
    device.write_gds(gds_filename)
    
    print(f"Successfully created '{gds_filename}' with footprint 4x240 um.")