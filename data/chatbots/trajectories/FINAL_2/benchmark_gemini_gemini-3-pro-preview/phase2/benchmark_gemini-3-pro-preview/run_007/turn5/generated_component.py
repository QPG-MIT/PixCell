import gdsfactory as gf

@gf.cell
def device_recreation_refined_v3():
    """
    Refined recreation of the device geometry matching the footprint [25, 10].
    
    Adjustments from previous iteration:
    1.  Increased Top Finger Width (3.2 -> 4.6) and Pitch (6.0 -> 6.4) to match the visual 
        density of the target. The target image displays stout fingers with relatively 
        narrow gaps, whereas the previous iteration had wide gaps.
    2.  This change pushes the outer fingers closer to the edge of the block, reducing 
        the 'shoulder' width to ~0.6um, which better matches the silhouette.
    3.  Adjusted taper of top fingers to be more subtle (4.6->3.8) to match the 
        columnar appearance in the target.
    4.  Widened the base of the bottom finger to anchor it visually.
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
    # Refined Pitch and Width to reduce gaps and shoulders.
    # Target visual: Fingers are dominant, gaps are narrow stripes.
    # Pitch = 6.4um, Width = 4.6um -> Gap = 1.8um.
    # Outer edge = 1.5 * 6.4 + 4.6/2 = 9.6 + 2.3 = 11.9.
    # Block edge = 12.5. Shoulder = 0.6um.
    pitch = 6.4
    
    # Finger dimensions
    # Stout, slightly tapered fingers
    finger_width_base = 4.6
    finger_width_tip = 3.8 
    
    # Bottom finger dimensions
    # Fits visually as a sharp spike
    bot_finger_width_base = 3.0 
    bot_finger_width_tip = 0.5 
    
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
    device = device_recreation_refined_v3()
    device.write_gds("device_recreation_refined_v3.gds")
    device.show()