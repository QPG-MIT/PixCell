import gdsfactory as gf

@gf.cell
def device_recreation_refined():
    """
    Refined recreation of the device geometry matching the thicker profile and specific asymmetry.
    Constraints: Footprint [25um, 10um].
    """
    c = gf.Component()
    layer = (1, 0)

    # ---------------------------------------------------------
    # Dimensions
    # ---------------------------------------------------------
    total_width = 25.0
    
    # Vertical budget distribution (Total = 10.0)
    # Block is the dominant visual element, followed by top fingers.
    blk_height = 5.0
    top_finger_len = 3.5
    bot_finger_len = 1.5
    
    # Horizontal alignment
    # The finger array is shifted left relative to the block center.
    # Calculated to create a small left margin (~2um) and large right margin.
    finger_assembly_offset = -3.5

    # ---------------------------------------------------------
    # 1. Main Body
    # ---------------------------------------------------------
    rect = c << gf.components.rectangle(
        size=(total_width, blk_height),
        layer=layer,
        centered=True
    )

    # ---------------------------------------------------------
    # 2. Top Fingers
    # ---------------------------------------------------------
    # Substantial tapered fingers (not slender needles)
    taper_top = gf.components.taper(
        length=top_finger_len,
        width1=2.15,  # Robust base width
        width2=1.5,   # Moderate taper to flat tip
        layer=layer
    )

    # Pitch logic: Spacing the 4 fingers
    pitch = 4.0
    # Centered indices [-1.5, -0.5, 0.5, 1.5] relative to the group center
    finger_indices = [-1.5, -0.5, 0.5, 1.5] 
    
    y_top_attach = blk_height / 2

    for i in finger_indices:
        x_local = i * pitch
        
        ref = c << taper_top
        ref.rotate(90)
        # Move to position: Group offset + Local index position
        ref.move((finger_assembly_offset + x_local, y_top_attach))

    # ---------------------------------------------------------
    # 3. Bottom Finger
    # ---------------------------------------------------------
    # Short, stout taper
    taper_bot = gf.components.taper(
        length=bot_finger_len,
        width1=2.4,   # Wide base, roughly matching the gap width above
        width2=1.0,   # Tapers to a smaller tip
        layer=layer
    )
    
    y_bot_attach = -blk_height / 2
    
    ref_bot = c << taper_bot
    ref_bot.rotate(-90)
    # Aligned with the center of the top finger group (between the middle two fingers)
    ref_bot.move((finger_assembly_offset, y_bot_attach))

    return c

if __name__ == "__main__":
    device = device_recreation_refined()
    device.write_gds("device_recreation_refined.gds")
    device.show()