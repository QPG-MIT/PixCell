import gdsfactory as gf

@gf.cell
def device_reconstruction_refined():
    """
    Refined recreation of the directional coupler.
    Adjustments made to match visual proportions:
    - Thicker outer rails (0.8um) to match the 'heavy' look of the handles.
    - Compact central bus to fit within the 4um height budget.
    - Maximized S-bend flare to touch the 4um boundary.
    """
    c = gf.Component()

    # --- Parameters ---
    # Global Constraints
    total_length = 120.0
    total_height_limit = 4.0   # y goes from -2.0 to 2.0
    max_y_abs = total_height_limit / 2.0
    
    # Longitudinal Dimensions
    bend_length = 15.0
    straight_length = total_length - (2 * bend_length) # 90.0um
    
    # Cross-sectional Geometry (Y-axis)
    # 1. Central Bus (4 thin lines, tight spacing)
    n_inner_lines = 4
    inner_width = 0.15
    inner_gap = 0.1     # Tighter gap to save vertical space
    
    # 2. Outer Rails (Thick "handles")
    rail_width = 0.8    # Increased width to match visual weight
    rail_gap = 0.15     # Gap between central bus and outer rail
    
    # --- Calculations ---
    
    # 1. Calculate Bus Height
    # Height = (N * width) + ((N-1) * gap)
    bus_stack_height = (n_inner_lines * inner_width) + ((n_inner_lines - 1) * inner_gap)
    # bus_stack_height = (4 * 0.15) + (3 * 0.1) = 0.6 + 0.3 = 0.9 um
    
    # 2. Calculate Rail Position (Straight Section)
    # Center Y of the straight rail
    # Y = (Half bus height) + gap + (half rail width)
    y_rail_center_straight = (bus_stack_height / 2) + rail_gap + (rail_width / 2)
    # y = 0.45 + 0.15 + 0.4 = 1.0 um
    
    # 3. Calculate Max Bend Offset (dy)
    # The rail flares OUT at the ends. We want to use the remaining space up to the 4um limit.
    # Top edge of straight rail = y_rail_center_straight + rail_width/2 = 1.4 um
    # Space remaining = 2.0 - 1.4 = 0.6 um
    # We leave a tiny margin (0.05) to avoid rounding errors putting it off-grid/outside
    dy = max_y_abs - (y_rail_center_straight + rail_width/2) - 0.05
    
    print(f"Computed Geometry:")
    print(f"Bus Height: {bus_stack_height}um")
    print(f"Rail Straight Center Y: {y_rail_center_straight}um")
    print(f"Max Bend Offset (dy): {dy}um")

    # --- Cross Sections ---
    xs_inner = gf.cross_section.cross_section(width=inner_width, layer=(1, 0))
    xs_rail = gf.cross_section.cross_section(width=rail_width, layer=(1, 0))

    # --- Construction: 1. Central Bus ---
    # 4 parallel lines, straight, full length
    for i in range(n_inner_lines):
        # Grid index centered around 0
        # i=0 is bottom-most, i=3 is top-most
        offset_from_bottom = i * (inner_width + inner_gap)
        y_pos = -bus_stack_height/2 + (inner_width/2) + offset_from_bottom
        
        wg = c << gf.components.straight(length=total_length, cross_section=xs_inner)
        wg.x = 0
        wg.y = y_pos

    # --- Construction: 2. Top Rail ---
    # Structure: Bend_Up -> Straight -> Bend_Up
    
    # Middle Straight Section
    top_straight = c << gf.components.straight(length=straight_length, cross_section=xs_rail)
    top_straight.x = 0
    top_straight.y = y_rail_center_straight
    
    # Left Bend (Flares UP to the left)
    # We connect the END (o2) of the bend to the START (o1) of the straight section.
    # bend_s(size=(L, h)). o2 is at (L, h).
    # To have the input higher than the straight section, we need a negative drop from input to output.
    # Or simply: Input (high) -> S-Bend -> Output (low).
    # We use size=(L, -dy) to drop DOWN from left to right.
    top_bend_left = c << gf.components.bend_s(size=(bend_length, -dy), cross_section=xs_rail)
    top_bend_left.connect("o2", top_straight.ports["o1"])
    
    # Right Bend (Flares UP to the right)
    # Connect start (o1) of bend to end (o2) of straight.
    # We need to go UP. size=(L, dy).
    top_bend_right = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs_rail)
    top_bend_right.connect("o1", top_straight.ports["o2"])

    # --- Construction: 3. Bottom Rail ---
    # Symmetric to top
    
    # Middle Straight Section
    bot_straight = c << gf.components.straight(length=straight_length, cross_section=xs_rail)
    bot_straight.x = 0
    bot_straight.y = -y_rail_center_straight
    
    # Left Bend (Flares DOWN to the left)
    # Input (low) -> S-Bend -> Output (high/center).
    # This is a rise of +dy from left to right.
    bot_bend_left = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs_rail)
    bot_bend_left.connect("o2", bot_straight.ports["o1"])
    
    # Right Bend (Flares DOWN to the right)
    # Output (low). Drop of -dy.
    bot_bend_right = c << gf.components.bend_s(size=(bend_length, -dy), cross_section=xs_rail)
    bot_bend_right.connect("o1", bot_straight.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=top_bend_left.ports["o1"])
    c.add_port("o2", port=bot_bend_left.ports["o1"])
    c.add_port("o3", port=top_bend_right.ports["o2"])
    c.add_port("o4", port=bot_bend_right.ports["o2"])

    return c

if __name__ == "__main__":
    device = device_reconstruction_refined()
    device.show()
    device.write_gds("reconstructed_coupler_refined.gds")