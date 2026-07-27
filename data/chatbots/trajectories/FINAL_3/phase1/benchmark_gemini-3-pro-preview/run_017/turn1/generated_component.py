import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Creates a directional coupler matching the visual input and footprint constraints.
    Footprint: 4 um (height) x 240 um (length).
    """
    c = gf.Component()

    # --- 1. Parameters ---
    total_length = 240.0
    total_height = 4.0
    
    # Waveguide specs
    wg_width = 0.5
    gap = 0.2
    
    # Geometry calculations
    # We apportion the length: 70um bend + 100um straight + 70um bend = 240um
    coupling_length = 100.0
    bend_length = (total_length - coupling_length) / 2
    
    # Calculate Vertical Shift (dy) for the S-bends
    # Inner Y position (center of waveguide in coupling region)
    y_inner = (gap + wg_width) / 2.0
    # Outer Y position (center of waveguide at ports)
    # Assuming 4.0 is the bounding box height, centers are offset by half width
    y_outer = (total_height - wg_width) / 2.0
    
    dy = y_outer - y_inner

    # --- 2. Create Primitives ---
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width)

    # Central Straight Section (The Coupler)
    # We use two straight waveguides placed closer together
    straight_wg = gf.components.straight(length=coupling_length, cross_section=xs)

    # S-Bend (The transition)
    # We define a bend that moves 'length' in X and 'dy' in Y
    s_bend = gf.components.bend_s(size=(bend_length, dy), cross_section=xs)


    # --- 3. Assembly (Place and Connect) ---

    # -- Middle Section --
    # Place top straight
    wg_top = c << straight_wg
    wg_top.movey(y_inner)
    
    # Place bottom straight
    wg_bot = c << straight_wg
    wg_bot.movey(-y_inner)

    # -- Input Section (Left) --
    # Top Left Bend (needs to go UP from coupler to port, so we mirror the s_bend)
    # Note: bend_s usually starts at (0,0). 
    
    bl_top = c << s_bend
    bl_top.mirror_y() # Flip so it goes "up" and "left" conceptually when we connect
    bl_top.connect("o2", wg_top.ports["o1"]) # Connect end of bend to start of straight

    bl_bot = c << s_bend
    bl_bot.connect("o2", wg_bot.ports["o1"]) # Standard S-bend goes down-to-up or up-to-down depending on signs

    # -- Output Section (Right) --
    br_top = c << s_bend
    br_top.connect("o1", wg_top.ports["o2"]) # Connect start of bend to end of straight
    
    br_bot = c << s_bend
    br_bot.mirror_y()
    br_bot.connect("o1", wg_bot.ports["o2"])


    # --- 4. Expose Ports ---
    c.add_port("o1", port=bl_top.ports["o1"]) # Top Input
    c.add_port("o2", port=bl_bot.ports["o1"]) # Bottom Input
    c.add_port("o3", port=br_top.ports["o2"]) # Top Output
    c.add_port("o4", port=br_bot.ports["o2"]) # Bottom Output

    return c

# Create and save the device
device = directional_coupler_4x240()
device.write_gds("directional_coupler_recreated.gds")
device.show()