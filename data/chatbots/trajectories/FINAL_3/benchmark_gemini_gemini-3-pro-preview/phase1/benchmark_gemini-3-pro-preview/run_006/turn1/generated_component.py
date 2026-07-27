import gdsfactory as gf

@gf.cell
def directional_coupler_custom():
    """
    Creates a directional coupler matching the provided image and footprint.
    Footprint: 120um x 4um
    """
    c = gf.Component()

    # --- Dimensions ---
    # Total footprint constraints
    total_length = 120.0
    total_height = 4.0
    
    # Waveguide specs
    wg_width = 0.5
    coupling_gap = 0.2
    
    # Calculate lengths derived from visual aspect ratio (roughly 1:1:1 split)
    # 40um bend + 40um straight + 40um bend = 120um total
    length_bend = 40.0
    length_coupling = 40.0
    
    # Calculate vertical shifts (dy)
    # Inner y position (center of waveguides in coupling region)
    # Spacing = gap + width = 0.2 + 0.5 = 0.7
    y_inner = (coupling_gap + wg_width) / 2  # +/- 0.35
    
    # Outer y position (center of waveguides at ports)
    # Total height 4.0 means edges are at +/- 2.0.
    # Center = Edge - width/2 = 2.0 - 0.25 = 1.75
    y_outer = (total_height / 2) - (wg_width / 2) # +/- 1.75
    
    # The vertical shift for the S-bend
    dy = y_outer - y_inner # 1.75 - 0.35 = 1.4

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Central Coupling Region ---
    # Create the two parallel straight waveguides
    wg_coup_top = c << gf.components.straight(length=length_coupling, cross_section=xs)
    wg_coup_bot = c << gf.components.straight(length=length_coupling, cross_section=xs)

    # Position them vertically
    wg_coup_top.movey(y_inner)
    wg_coup_bot.movey(-y_inner)

    # --- 2. Left Input Transitions (Converging) ---
    # Top Input: S-bend going DOWN (-dy) to meet the straight section
    # We connect the END (o2) of the bend to the START (o1) of the straight
    bend_in_top = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_in_top.connect("o2", wg_coup_top.ports["o1"])

    # Bottom Input: S-bend going UP (+dy) to meet the straight section
    bend_in_bot = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_in_bot.connect("o2", wg_coup_bot.ports["o1"])

    # --- 3. Right Output Transitions (Diverging) ---
    # Top Output: S-bend going UP (+dy) away from the straight section
    # We connect the START (o1) of the bend to the END (o2) of the straight
    bend_out_top = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_out_top.connect("o1", wg_coup_top.ports["o2"])

    # Bottom Output: S-bend going DOWN (-dy) away from the straight section
    bend_out_bot = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_coup_bot.ports["o2"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=bend_in_top.ports["o1"]) # Top Left
    c.add_port("o2", port=bend_in_bot.ports["o1"]) # Bottom Left
    c.add_port("o3", port=bend_out_top.ports["o2"]) # Top Right
    c.add_port("o4", port=bend_out_bot.ports["o2"]) # Bottom Right

    return c

# Create and save the GDS
device = directional_coupler_custom()
device.write_gds("directional_coupler_custom.gds")