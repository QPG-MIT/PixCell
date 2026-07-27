import gdsfactory as gf

@gf.cell
def device_recreation_refined_v2():
    """
    Refined recreation of the device geometry matching the footprint [25, 10].
    
    Adjustments:
    1.  Increased prong pitch and width significantly to fill the 25um width 
        constraint, eliminating the large empty shoulders seen in the previous iteration.
    2.  Centered the array symmetrically on the block (fixing the left-shift).
    3.  Maintained vertical proportions (Block ~45%, Prongs ~40%/15%) to match 
        the visual weight of the components within the 10um height budget.
    """
    c = gf.Component()
    layer = (1, 0)

    # ---------------------------------------------------------
    # Dimensions (Constraints: 25 x 10)
    # ---------------------------------------------------------
    total_width = 25.0
    
    # Vertical partitioning (Total Height = 10.0)
    # Block is the anchor, occupying roughly 45% of height
    blk_height = 4.5
    # Top fingers occupy roughly 40%
    top_finger_len = 4.0
    # Bottom finger occupies remaining 15%
    bot_finger_len = 1.5
    
    # Horizontal partitioning (Total Width = 25.0)
    # The prong array needs to visually balance the block width.
    # We aim for the array to span ~21-22um, leaving ~1.5-2um margins.
    # Calculation: 3 gaps + 4 fingers.
    # If Pitch = 6.0um, span center-to-center is 18um. 
    # With finger width ~3.2um, total span is 21.2um.
    pitch = 6.0
    
    # Finger dimensions
    # Stout, tapered fingers to fill the horizontal space
    finger_width_base = 3.2
    finger_width_tip = 2.4  # Moderate taper to a flat tip
    
    # Bottom finger dimensions
    # Fits roughly in the gap between the two central top fingers
    # Gap ~ Pitch - finger_width_base = 6.0 - 3.2 = 2.8
    bot_finger_width_base = 2.8 
    bot_finger_width_tip = 0.8 # Sharper point
    
    # ---------------------------------------------------------
    # 1. Main Body (Block)
    # ---------------------------------------------------------
    # Centered at (0,0) for symmetry
    rect = c << gf.components.rectangle(
        size=(total_width, blk_height),
        layer=layer,
        centered=True
    )

    # ---------------------------------------------------------
    # 2. Top Fingers
    # ---------------------------------------------------------
    finger_top = gf.components.taper(
        length=top_finger_len,
        width1=finger_width_base,
        width2=finger_width_tip,
        layer=layer
    )
    
    # Center positions relative to 0
    # Indices correspond to: -1.5, -0.5, 0.5, 1.5 multiples of pitch
    finger_indices = [-1.5, -0.5, 0.5, 1.5]
    y_top_attach = blk_height / 2
    
    for i in finger_indices:
        x_pos = i * pitch
        ref = c << finger_top
        ref.rotate(90) # Rotate to point upwards
        ref.move((x_pos, y_top_attach))

    # ---------------------------------------------------------
    # 3. Bottom Finger
    # ---------------------------------------------------------
    finger_bot = gf.components.taper(
        length=bot_finger_len,
        width1=bot_finger_width_base,
        width2=bot_finger_width_tip,
        layer=layer
    )
    
    y_bot_attach = -blk_height / 2
    
    ref_bot = c << finger_bot
    ref_bot.rotate(-90) # Rotate to point downwards
    # Centered horizontally at 0
    ref_bot.move((0, y_bot_attach))

    return c

if __name__ == "__main__":
    device = device_recreation_refined_v2()
    device.write_gds("device_recreation_refined_v2.gds")
    device.show()