import gdsfactory as gf

@gf.cell
def device_recreation():
    """
    Recreates the device geometry from the image using parametric primitives.
    Constraints: Footprint [25um, 10um].
    """
    c = gf.Component()
    
    # Layer definition
    layer = (1, 0)
    
    # ---------------------------------------------------------
    # Parameters
    # ---------------------------------------------------------
    # Footprint constraint: 25 x 10
    total_width = 25.0
    
    # Vertical partition (sum = 10.0)
    body_height = 5.0
    top_finger_length = 3.5
    bot_finger_length = 1.5
    
    # ---------------------------------------------------------
    # 1. Main Body (Rectangle)
    # ---------------------------------------------------------
    # Centered at (0,0)
    rect = c << gf.components.rectangle(
        size=(total_width, body_height),
        layer=layer,
        centered=True
    )
    
    # ---------------------------------------------------------
    # 2. Top Fingers (4x Tapers)
    # ---------------------------------------------------------
    # These appear slender.
    # width1 = base (attached to rect), width2 = tip
    taper_top = gf.components.taper(
        length=top_finger_length,
        width1=2.0,
        width2=1.0,
        layer=layer
    )
    
    # Pitch setup: 4 fingers centered. 
    # Pitch of 4.0um gives positions [-6, -2, 2, 6]
    finger_x_positions = [-6.0, -2.0, 2.0, 6.0]
    
    # Y-coordinate for attachment (top edge of rectangle)
    y_top_edge = body_height / 2
    
    for x in finger_x_positions:
        # Add reference
        ref = c << taper_top
        # Rotate 90 degrees (taper points +x by default, now points +y)
        ref.rotate(90)
        # Move base to the attachment point
        ref.move((x, y_top_edge))

    # ---------------------------------------------------------
    # 3. Bottom Finger (1x Taper)
    # ---------------------------------------------------------
    # This appears shorter and wider.
    taper_bot = gf.components.taper(
        length=bot_finger_length,
        width1=3.0,
        width2=1.5,
        layer=layer
    )
    
    # Y-coordinate for attachment (bottom edge of rectangle)
    y_bot_edge = -body_height / 2
    
    # Add reference
    ref_bot = c << taper_bot
    # Rotate -90 degrees (points -y)
    ref_bot.rotate(-90)
    # Move base to the attachment point
    ref_bot.move((0, y_bot_edge))
    
    return c

# Create and save the component
if __name__ == "__main__":
    device = device_recreation()
    device.write_gds("device_recreation.gds")
    device.show()