import gdsfactory as gf

@gf.cell
def trident_mode_converter():
    """
    Generates a trident-shaped mode converter / inverse taper coupler.
    
    Dimensions derived from footprint (40.0, 1.7):
    - Length: 40.0 um
    - Vertical span: 1.7 um (0.5 top + 0.2 gap + 0.3 mid + 0.2 gap + 0.5 bot)
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    length = 40.0
    width_outer = 0.5
    width_inner = 0.3
    gap = 0.2
    
    # Layer definition (Standard waveguide layer)
    layer_wg = (1, 0)
    
    # Define Cross Section for outer arms
    xs_outer = gf.cross_section.cross_section(width=width_outer, layer=layer_wg)

    # --- Calculate Positions ---
    # Input Y positions (Left side)
    # y=0 is the center of the device.
    # Center of top waveguide:
    y_top_start = (width_inner / 2) + gap + (width_outer / 2) # 0.15 + 0.2 + 0.25 = 0.6
    y_bot_start = -y_top_start
    
    # Output Y positions (Right side)
    # The outer arms converge. We assume they touch/merge at y=0.
    # Center of top waveguide at merge: +width/2
    y_top_end = width_outer / 2
    y_bot_end = -width_outer / 2
    
    # Calculate vertical shift (dy) for the S-bends
    dy_top = y_top_end - y_top_start # Negative shift (down)
    dy_bot = y_bot_end - y_bot_start # Positive shift (up)

    # --- 1. Central Taper ---
    # The taper terminates before the end of the device.
    # Visually estimated at 30um length based on the crop.
    taper_length = 30.0
    
    taper = c << gf.components.taper(
        length=taper_length,
        width1=width_inner,
        width2=0.0,
        layer=layer_wg
    )
    # Taper default placement is at (0,0), which aligns with our center.

    # --- 2. Top Arm (S-Bend) ---
    # Uses an S-bend to adiabatically transition from start to end Y positions.
    bend_top = c << gf.components.bend_s(
        size=(length, dy_top),
        cross_section=xs_outer
    )
    # Move the bend to the starting position
    bend_top.move((0, y_top_start))

    # --- 3. Bottom Arm (S-Bend) ---
    bend_bot = c << gf.components.bend_s(
        size=(length, dy_bot),
        cross_section=xs_outer
    )
    # Move the bend to the starting position
    bend_bot.move((0, y_bot_start))

    # --- Add Ports (Optional but good practice) ---
    c.add_port("o1_top", port=bend_top.ports["o1"])
    c.add_port("o1_mid", port=taper.ports["o1"])
    c.add_port("o1_bot", port=bend_bot.ports["o1"])
    # The output ports are at the end of the bends
    c.add_port("o2", port=bend_top.ports["o2"]) 

    return c

# Generate and save the device
if __name__ == "__main__":
    device = trident_mode_converter()
    device.show() # Shows geometry in KLayout if installed
    device.write_gds("trident_coupler.gds")