import gdsfactory as gf

@gf.cell
def device_recreation_refined():
    """
    Refined recreation of the device geometry matching the slender profile and asymmetry.
    Constraints: Footprint [25um, 10um].
    """
    c = gf.Component()
    layer = (1, 0)

    # ---------------------------------------------------------
    # Dimensions
    # ---------------------------------------------------------
    total_width = 25.0
    
    # Redistribution of the 10.0um vertical budget for a slender look
    top_finger_len = 4.25
    body_height = 4.25
    bot_finger_len = 1.5
    
    # Horizontal alignment
    # The finger array appears shifted left relative to the block center in the target image.
    finger_assembly_offset = -2.0

    # ---------------------------------------------------------
    # 1. Main Body
    # ---------------------------------------------------------
    rect = c << gf.components.rectangle(
        size=(total_width, body_height),
        layer=layer,
        centered=True
    )

    # ---------------------------------------------------------
    # 2. Top Fingers
    # ---------------------------------------------------------
    # Slender taper: narrower base and longer length
    taper_top = gf.components.taper(
        length=top_finger_len,
        width1=1.3,  # Narrow base
        width2=0.8,  # Tip
        layer=layer
    )

    # Pitch logic: Spacing the 4 fingers
    pitch = 4.0
    # Centered indices [-1.5, -0.5, 0.5, 1.5] relative to the *group center*
    finger_indices = [-1.5, -0.5, 0.5, 1.5] 
    
    y_top_attach = body_height / 2

    for i in finger_indices:
        x_local = i * pitch
        
        ref = c << taper_top
        ref.rotate(90)
        # Move to position: Local index position + Global offset
        ref.move((x_local + finger_assembly_offset, y_top_attach))

    # ---------------------------------------------------------
    # 3. Bottom Finger
    # ---------------------------------------------------------
    # Short, sharper taper
    taper_bot = gf.components.taper(
        length=bot_finger_len,
        width1=1.8, 
        width2=0.6,
        layer=layer
    )
    
    y_bot_attach = -body_height / 2
    
    ref_bot = c << taper_bot
    ref_bot.rotate(-90)
    # Aligned with the top finger group
    ref_bot.move((finger_assembly_offset, y_bot_attach))

    return c

if __name__ == "__main__":
    device = device_recreation_refined()
    device.write_gds("device_recreation_refined.gds")
    device.show()