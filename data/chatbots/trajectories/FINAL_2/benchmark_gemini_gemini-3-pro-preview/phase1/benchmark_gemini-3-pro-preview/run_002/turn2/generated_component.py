import gdsfactory as gf

@gf.cell
def mmi_1x4_splitter():
    """
    Creates a 1x4 MMI splitter.
    
    Refinements based on visual feedback:
    - Increased taper tip width to avoid "needle" look.
    - Widened port pitch to match the spread in the original image.
    - Adjusted vertical proportions to fit 25x10um footprint.
    """
    c = gf.Component("mmi_1x4_splitter")
    layer = (1, 0)

    # --- Dimensions ---
    # Total Footprint: 25.0 x 10.0 um
    
    # Vertical budget allocation (Total = 10.0)
    body_height = 5.8
    taper_top_len = 3.0
    taper_bot_len = 1.2
    
    # Horizontal dimensions
    body_width = 25.0
    
    # Widths
    # width_base: Width of taper at the MMI body interface
    # width_tip: Width of the waveguide port (increased to 0.8 to match visual thickness)
    width_base = 2.0
    width_tip = 0.8

    # --- 1. MMI Body ---
    # Central multimode mixing region
    body = c << gf.components.rectangle(
        size=(body_width, body_height), 
        layer=layer, 
        centered=True
    )

    # --- 2. Top Output Tapers ---
    # Previous pitch (5.0) left too much empty space on the sides.
    # Increasing pitch to 6.25 (W/N) spreads tapers closer to the edges.
    # Positions: +/- 3.125, +/- 9.375
    x_positions = [-9.375, -3.125, 3.125, 9.375]
    
    taper_top = gf.components.taper(
        length=taper_top_len,
        width1=width_base,
        width2=width_tip,
        layer=layer
    )

    for i, x in enumerate(x_positions):
        ref = c << taper_top
        ref.rotate(90)  # Point Up
        ref.move((x, body_height / 2))
        c.add_port(f"o{i+2}", port=ref.ports["o2"])

    # --- 3. Bottom Input Taper ---
    # Shorter, stubbier taper at the bottom
    taper_bot = gf.components.taper(
        length=taper_bot_len,
        width1=width_base,
        width2=width_tip,
        layer=layer
    )

    ref_bot = c << taper_bot
    ref_bot.rotate(-90)  # Point Down
    ref_bot.move((0, -body_height / 2))
    c.add_port("o1", port=ref_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate and save
    device = mmi_1x4_splitter()
    device.write_gds("mmi_1x4_splitter.gds")
    print("GDS file 'mmi_1x4_splitter.gds' has been generated.")