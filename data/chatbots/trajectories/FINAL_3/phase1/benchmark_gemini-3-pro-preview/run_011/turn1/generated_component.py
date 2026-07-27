import gdsfactory as gf

@gf.cell
def directional_coupler_device():
    """
    Parametric recreation of the directional coupler.
    Footprint constraints: 240 um (length) x 4 um (width).
    """
    c = gf.Component()

    # --- 1. Parameters ---
    # Global Dimensions
    length_total = 240.0
    width_footprint = 4.0
    
    # Waveguide Physics
    wg_width = 0.5
    gap_coupling = 0.2
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 2. Geometry Calculation ---
    # To fit exactly 240um length, we define lengths for bends and straights
    # Let's allocate 20um for the S-bend transitions on each side
    length_bend = 20.0
    length_straight = length_total - (2 * length_bend) # 200.0 um

    # Calculate Vertical Offsets (Y-axis)
    # The footprint is 4um. Assuming this is the outer bounds:
    # Top waveguide center y = (4.0/2) - (0.5/2) = 1.75
    # Bottom waveguide center y = -1.75
    # Distance between input ports (center-to-center) = 3.5 um
    y_input_top = 1.75
    y_input_bot = -1.75

    # Coupling region separation
    # Center-to-center distance = wg_width + gap = 0.5 + 0.2 = 0.7 um
    y_couple_top = 0.35
    y_couple_bot = -0.35

    # Calculate the vertical shift (dy) required for the S-bends
    # How much does the top waveguide need to move down? 1.75 -> 0.35
    dy_top_in = y_couple_top - y_input_top   # -1.4
    dy_bot_in = y_couple_bot - y_input_bot   # 1.4

    # --- 3. Component Assembly ---

    # --- TOP ARM ---
    # 1. Input S-Bend (Top)
    # bend_s size is (length, height_change)
    sbend_top_in = c << gf.components.bend_s(
        size=(length_bend, dy_top_in), 
        cross_section=xs
    )
    # Move start point to correct input location
    sbend_top_in.movey(y_input_top)

    # 2. Coupling Straight (Top)
    straight_top = c << gf.components.straight(
        length=length_straight, 
        cross_section=xs
    )
    straight_top.connect("o1", sbend_top_in.ports["o2"])

    # 3. Output S-Bend (Top) - Bends back up (positive dy)
    sbend_top_out = c << gf.components.bend_s(
        size=(length_bend, -dy_top_in), # Reverse the shift to go back out
        cross_section=xs
    )
    sbend_top_out.connect("o1", straight_top.ports["o2"])


    # --- BOTTOM ARM ---
    # 1. Input S-Bend (Bottom)
    sbend_bot_in = c << gf.components.bend_s(
        size=(length_bend, dy_bot_in), 
        cross_section=xs
    )
    sbend_bot_in.movey(y_input_bot)

    # 2. Coupling Straight (Bottom)
    straight_bot = c << gf.components.straight(
        length=length_straight, 
        cross_section=xs
    )
    straight_bot.connect("o1", sbend_bot_in.ports["o2"])

    # 3. Output S-Bend (Bottom) - Bends back down (negative dy)
    sbend_bot_out = c << gf.components.bend_s(
        size=(length_bend, -dy_bot_in),
        cross_section=xs
    )
    sbend_bot_out.connect("o1", straight_bot.ports["o2"])

    # --- 4. Define Ports ---
    c.add_port("o1", port=sbend_top_in.ports["o1"])
    c.add_port("o2", port=sbend_bot_in.ports["o1"])
    c.add_port("o3", port=sbend_top_out.ports["o2"])
    c.add_port("o4", port=sbend_bot_out.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate the component
    dc = directional_coupler_device()
    
    # Save directly to GDS file
    gds_path = dc.write_gds("directional_coupler.gds")
    
    print(f"Geometry successfully written to: {gds_path}")