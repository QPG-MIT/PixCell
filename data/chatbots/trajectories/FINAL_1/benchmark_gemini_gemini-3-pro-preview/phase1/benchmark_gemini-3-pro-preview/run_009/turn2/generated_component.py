import gdsfactory as gf

@gf.cell
def trident_mode_converter():
    """
    Generates a trident-shaped mode converter with a straight input section
    and merging output arms.
    
    Dimensions derived from footprint (40.0, 1.7):
    - Total Length: 40.0 um
    - Input Height: 1.7 um (0.5 top + 0.2 gap + 0.3 mid + 0.2 gap + 0.5 bot)
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    length_total = 40.0
    length_straight = 12.0  # Length of the parallel input section
    length_bend = length_total - length_straight
    
    width_outer = 0.5
    width_inner = 0.3
    gap_input = 0.2
    
    # Layer definition
    layer_wg = (1, 0)
    xs = gf.cross_section.cross_section(width=width_outer, layer=layer_wg)

    # --- Y-Position Calculations ---
    # Input Y positions (Left side) - determined by footprint 1.7um height
    # Top center: (0.3/2) + 0.2 + (0.5/2) = 0.15 + 0.2 + 0.25 = 0.6
    y_in_top = 0.6
    y_in_bot = -0.6
    
    # Output Y positions (Right side)
    # The outer arms merge into a single waveguide block.
    # To ensure a solid merge, we overlap them slightly.
    # If centers are at +/- 0.15, inner edges are at +/- (0.15 - 0.25) = -/+ 0.1 (0.2um overlap)
    y_out_top = 0.15
    y_out_bot = -0.15
    
    # Calculate vertical shift for S-bends
    dy_top = y_out_top - y_in_top
    dy_bot = y_out_bot - y_in_bot

    # --- 1. Central Taper ---
    # Taper extends into the merging region but terminates before the end
    taper = c << gf.components.taper(
        length=35.0,
        width1=width_inner,
        width2=0.0,
        layer=layer_wg
    )
    # Taper placed at (0,0) by default

    # --- 2. Top Arm Construction ---
    # Segment 1: Straight parallel section
    top_straight = c << gf.components.straight(
        length=length_straight, 
        cross_section=xs
    )
    top_straight.move((0, y_in_top))
    
    # Segment 2: Adiabatic S-bend merging inwards
    top_bend = c << gf.components.bend_s(
        size=(length_bend, dy_top), 
        cross_section=xs
    )
    top_bend.connect("o1", top_straight.ports["o2"])

    # --- 3. Bottom Arm Construction ---
    # Segment 1: Straight parallel section
    bot_straight = c << gf.components.straight(
        length=length_straight, 
        cross_section=xs
    )
    bot_straight.move((0, y_in_bot))
    
    # Segment 2: Adiabatic S-bend merging inwards
    bot_bend = c << gf.components.bend_s(
        size=(length_bend, dy_bot), 
        cross_section=xs
    )
    bot_bend.connect("o1", bot_straight.ports["o2"])

    # --- Add Ports ---
    c.add_port("o1_top", port=top_straight.ports["o1"])
    c.add_port("o1_mid", port=taper.ports["o1"])
    c.add_port("o1_bot", port=bot_straight.ports["o1"])
    c.add_port("o2", port=top_bend.ports["o2"])

    return c

if __name__ == "__main__":
    device = trident_mode_converter()
    device.show()
    device.write_gds("trident_converter_corrected.gds")