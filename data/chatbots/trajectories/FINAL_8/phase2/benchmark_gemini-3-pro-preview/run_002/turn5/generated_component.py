import gdsfactory as gf

@gf.cell
def device_reconstruction_v4():
    """
    Refined reconstruction of the directional coupler (v4).
    
    Adjustments based on visual comparison:
    1.  **Proportions:** Inner line width increased to 0.18um and Rail width set to 0.75um.
        This achieves the observed ~1:4 thickness ratio.
    2.  **Spacing:** Gap between rail and bus increased to 0.18um to match the internal 
        bus spacing, creating a consistent 'grating' look.
    3.  **Bend Sharpness:** Reduced bend length to 9.0um. This makes the transitions 
        sharper and more distinct, matching the 'ears' in the reference image.
    4.  **Footprint Maximization:** Dynamic calculation ensures the output ports 
        touch exactly the +/- 2.0um vertical limits.
    """
    c = gf.Component()

    # --- Global Dimensions ---
    total_length = 120.0
    footprint_height = 4.0
    max_y_abs = footprint_height / 2.0
    
    # Longitudinal Geometry
    # Shortened bend length creates a steeper, more distinct curve
    bend_length = 9.0 
    straight_length = total_length - (2 * bend_length)

    # --- Cross-sectional Parameters ---
    # 1. Central Bus: Thicker lines for better definition
    n_inner_lines = 4
    inner_width = 0.18
    inner_gap = 0.18
    
    # 2. Outer Rails: Thick handles, balanced against the bus
    rail_width = 0.75 
    
    # 3. Gap between Central Bus and Outer Rail
    # Matched to inner_gap for uniform spacing appearance
    bus_to_rail_gap = 0.18

    # --- Geometry Calculation ---
    
    # Height of the inner 4-line stack
    bus_stack_height = (n_inner_lines * inner_width) + ((n_inner_lines - 1) * inner_gap)
    # Y-coordinate of the top of the bus (centered at y=0)
    bus_top_y = bus_stack_height / 2.0
    
    # Position of the Outer Rail (Straight Section)
    rail_inner_edge_y = bus_top_y + bus_to_rail_gap
    rail_center_y_straight = rail_inner_edge_y + (rail_width / 2.0)
    rail_top_edge_straight = rail_inner_edge_y + rail_width
    
    # S-Bend Height (dy) Calculation
    # Calculate how much the rail needs to flare out to touch the boundary
    # dy = (Limit) - (Current Top Edge)
    dy = max_y_abs - rail_top_edge_straight - 0.01 # 0.01um safety margin
    
    if dy < 0:
        print(f"Warning: Geometry exceeds footprint! Overlap: {-dy}um")
        dy = 0

    # --- Define Cross Sections ---
    xs_inner = gf.cross_section.cross_section(width=inner_width, layer=(1, 0))
    xs_rail = gf.cross_section.cross_section(width=rail_width, layer=(1, 0))

    # --- Construction: 1. Central Bus ---
    for i in range(n_inner_lines):
        # Calculate offset from bottom of the stack
        offset = i * (inner_width + inner_gap)
        # Center the group at Y=0
        y = -bus_stack_height/2 + inner_width/2 + offset
        
        wg = c << gf.components.straight(length=total_length, cross_section=xs_inner)
        wg.x = 0
        wg.y = y

    # --- Construction: 2. Top Rail ---
    # Structure: Bend_S (Up-Left) -> Straight -> Bend_S (Up-Right)
    
    # Middle Straight Section
    top_str = c << gf.components.straight(length=straight_length, cross_section=xs_rail)
    top_str.x = 0
    top_str.y = rail_center_y_straight
    
    # Left Bend (Flares UP to the left)
    # Input (high) -> Straight (low). Drop = -dy.
    bend_top_L = c << gf.components.bend_s(size=(bend_length, -dy), cross_section=xs_rail)
    bend_top_L.connect("o2", top_str.ports["o1"])
    
    # Right Bend (Flares UP to the right)
    # Straight (low) -> Output (high). Rise = +dy.
    bend_top_R = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs_rail)
    bend_top_R.connect("o1", top_str.ports["o2"])

    # --- Construction: 3. Bottom Rail ---
    # Symmetric to top rail
    
    # Middle Straight Section
    bot_str = c << gf.components.straight(length=straight_length, cross_section=xs_rail)
    bot_str.x = 0
    bot_str.y = -rail_center_y_straight
    
    # Left Bend (Flares DOWN to the left)
    # Input (low) -> Straight (high). Rise = +dy.
    bend_bot_L = c << gf.components.bend_s(size=(bend_length, dy), cross_section=xs_rail)
    bend_bot_L.connect("o2", bot_str.ports["o1"])
    
    # Right Bend (Flares DOWN to the right)
    # Straight (high) -> Output (low). Drop = -dy.
    bend_bot_R = c << gf.components.bend_s(size=(bend_length, -dy), cross_section=xs_rail)
    bend_bot_R.connect("o1", bot_str.ports["o2"])

    # --- Expose Ports ---
    c.add_port("o1", port=bend_top_L.ports["o1"])
    c.add_port("o2", port=bend_bot_L.ports["o1"])
    c.add_port("o3", port=bend_top_R.ports["o2"])
    c.add_port("o4", port=bend_bot_R.ports["o2"])

    return c

if __name__ == "__main__":
    device = device_reconstruction_v4()
    device.show()
    device.write_gds("reconstructed_coupler_v4.gds")