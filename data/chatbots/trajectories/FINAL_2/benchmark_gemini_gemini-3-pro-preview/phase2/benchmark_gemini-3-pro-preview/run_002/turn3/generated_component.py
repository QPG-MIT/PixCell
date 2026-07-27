import gdsfactory as gf

@gf.cell
def mmi_1x4_splitter():
    """
    Creates a 1x4 MMI splitter.
    
    Refinements:
    - Adjusted aspect ratio: Reduced body width to 12.0um to match the visual proportions 
      of the target image (the previous 25um width was too wide and flattened).
    - Vertical Budget: Tuned heights to sum exactly to 10.0um (Body 5.2 + Top 3.6 + Bot 1.2).
    - Taper Geometry: Defined taper base widths to create the distinct gap/finger pattern 
      seen in the reference.
    """
    c = gf.Component("mmi_1x4_splitter")
    layer = (1, 0)

    # --- Dimensions ---
    # Footprint Constraint: 25.0 x 10.0 um.
    # We use a width of 12.0um to maintain the correct visual aspect ratio 
    # (fitting well within the 25um limit).
    
    body_width = 12.0
    body_height = 5.2
    
    # Vertical lengths (Total = 10.0um)
    taper_top_len = 3.6
    taper_bot_len = 1.2
    
    # Widths
    # Tips: 0.6um (Standard single mode width)
    # Top Base: 1.4um (Creates visible gaps between waveguides)
    # Bot Base: 1.8um (Slightly wider input taper as seen in image)
    width_tip = 0.6
    width_top_base = 1.4
    width_bot_base = 1.8

    # Port Spacing
    # Pitch of 3.0um distributes 4 ports evenly across the 12um body 
    # with appropriate margins.
    pitch = 3.0
    x_positions = [-1.5 * pitch, -0.5 * pitch, 0.5 * pitch, 1.5 * pitch]

    # --- 1. MMI Body ---
    body = c << gf.components.rectangle(
        size=(body_width, body_height), 
        layer=layer, 
        centered=True
    )

    # --- 2. Top Output Tapers ---
    taper_top = gf.components.taper(
        length=taper_top_len,
        width1=width_top_base,
        width2=width_tip,
        layer=layer
    )

    for i, x in enumerate(x_positions):
        ref = c << taper_top
        ref.rotate(90)  # Point Up
        ref.move((x, body_height / 2))
        c.add_port(f"o{i+2}", port=ref.ports["o2"])

    # --- 3. Bottom Input Taper ---
    taper_bot = gf.components.taper(
        length=taper_bot_len,
        width1=width_bot_base,
        width2=width_tip,
        layer=layer
    )

    ref_bot = c << taper_bot
    ref_bot.rotate(-90)  # Point Down
    ref_bot.move((0, -body_height / 2))
    c.add_port("o1", port=ref_bot.ports["o2"])

    return c

if __name__ == "__main__":
    device = mmi_1x4_splitter()
    device.write_gds("mmi_1x4_splitter.gds")
    print("GDS file 'mmi_1x4_splitter.gds' has been generated.")