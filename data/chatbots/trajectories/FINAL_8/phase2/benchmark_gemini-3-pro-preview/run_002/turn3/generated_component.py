import gdsfactory as gf

@gf.cell
def device_reconstruction_final():
    """
    Final refined reconstruction of the directional coupler based on visual analysis.
    
    Key Adjustments:
    1. Inner Bus: Equalized line width and gap (0.16um) to create the distinct 
       striped pattern seen in the reference image.
    2. Outer Rails: Thickened to 0.85um to match the heavy visual weight of the handles.
    3. Flare Calculation: Dynamic calculation of S-bend height (dy) ensures the 
       device ports touch exactly the 4um height limit.
    """
    c = gf.Component()

    # --- Global Constraints ---
    # Footprint: 120um x 4um
    total_length = 120.0
    footprint_height = 4.0
    max_y_abs = footprint_height / 2.0
    
    # Longitudinal Geometry
    bend_length = 15.0
    straight_length = total_length - (2 * bend_length) # 90.0um
    
    # --- Cross-sectional Parameters (Y-axis) ---
    
    # 1. Central Bus (4 parallel lines)
    # Visual analysis suggests the white gaps are roughly equal to the black lines.
    n_inner_lines = 4
    inner_width = 0.16
    inner_gap = 0.16
    
    # 2. Outer Rails (Thick handles)
    rail_width = 0.85
    
    # 3. Separation
    # Gap between the central bus and the outer rail
    bus_to_rail_gap = 0.18
    
    # --- geometry Calculations ---
    
    # Calculate the total height of the inner bus stack
    # Height = (N * width) + ((N-1) * gap)
    bus_stack_height = (n_inner_lines * inner_width) + ((n_inner_lines - 1) * inner_gap)
    # Top Y coordinate of the bus (assuming centered at y=0)
    bus_top_y = bus_stack_height / 2.0
    
    # Calculate the center Y position of the straight rail section
    # Position = Bus Top + Gap + Half Rail Width
    rail_center_y_straight = bus_top_y + bus_to_rail_gap + (rail_width / 2.0)
    
    # Calculate the Maximum Flare (dy) for S-Bends
    # We want the input/output ports to touch the +/- 2.0um limit.
    # The straight section is closer to the center.
    # Current top edge of straight rail:
    rail_top_edge_straight = rail_center_y_straight + (rail_width / 2.0)
    
    # The flare height (dy) is the remaining space to the boundary
    flare_dy = max_y_abs - rail_top_edge_straight - 0.01 # 0.01 margin
    
    if flare_dy < 0:
        print("Warning: Inner components exceed vertical footprint!")
        flare_dy = 0

    # --- Cross Sections ---
    xs_inner = gf.cross_section.cross_section(width=inner_width, layer=(1, 0))
    xs_rail = gf.cross_section.cross_section(width=rail_width, layer=(1, 0))

    # --- Construction: 1. Central Bus ---
    # Create 4 parallel straight lines centered at y=0
    for i in range(n_inner_lines):
        # Calculate offset from the bottom of the stack
        offset_from_bottom = i * (inner_width + inner_gap)
        # Shift so the whole group is centered at y=0
        y_pos = -bus_stack_height/2 + (inner_width/2) + offset_from_bottom
        
        wg = c << gf.components.straight(length=total_length, cross_section=xs_inner)
        wg.x = 0
        wg.y = y_pos

    # --- Construction: 2. Top Rail ---
    # Structure: Bend_S (Left) -> Straight (Middle) -> Bend_S (Right)
    
    # Middle Straight Section
    top_str = c << gf.components.straight(length=straight_length, cross_section=xs_rail)
    top_str.x = 0
    top_str.y = rail_center_y_straight
    
    # Left Bend (Flares UP to the left)
    # We connect the END (o2) of the bend to the START (o1) of the straight.
    # Bend goes from Input -> Straight.
    # To drop DOWN from Input to Straight, use negative dy in bend_s size.
    top_bend_L = c << gf.components.bend_s(size=(bend_length, -flare_dy), cross_section=xs_rail)
    top_bend_L.connect("o2", top_str.ports["o1"])
    
    # Right Bend (Flares UP to the right)
    # Connect Start (o1) of bend to End (o2) of straight.
    # To rise UP from Straight to Output, use positive dy.
    top_bend_R = c << gf.components.bend_s(size=(bend_length, flare_dy), cross_section=xs_rail)
    top_bend_R.connect("o1", top_str.ports["o2"])

    # --- Construction: 3. Bottom Rail ---
    # Symmetric to top rail (Flares DOWN)
    
    # Middle Straight Section
    bot_str = c << gf.components.straight(length=straight_length, cross_section=xs_rail)
    bot_str.x = 0
    bot_str.y = -rail_center_y_straight
    
    # Left Bend (Flares DOWN to the left)
    # Input is lower than straight.
    # Bend goes Input -> Straight (Rise UP).
    # Positive dy rises from start to end.
    bot_bend_L = c << gf.components.bend_s(size=(bend_length, flare_dy), cross_section=xs_rail)
    bot_bend_L.connect("o2", bot_str.ports["o1"])
    
    # Right Bend (Flares DOWN to the right)
    # Straight -> Output (Drop DOWN).
    # Negative dy drops from start to end.
    bot_bend_R = c << gf.components.bend_s(size=(bend_length, -flare_dy), cross_section=xs_rail)
    bot_bend_R.connect("o1", bot_str.ports["o2"])

    # --- Ports ---
    c.add_port("o1", port=top_bend_L.ports["o1"])
    c.add_port("o2", port=bot_bend_L.ports["o1"])
    c.add_port("o3", port=top_bend_R.ports["o2"])
    c.add_port("o4", port=bot_bend_R.ports["o2"])

    return c

if __name__ == "__main__":
    device = device_reconstruction_final()
    device.show()
    device.write_gds("reconstructed_coupler_final.gds")