import gdsfactory as gf

@gf.cell
def device():
    """
    Creates the comb-like geometry with proper proportions.
    The device fits exactly within the specified [25, 10] footprint.
    """
    c = gf.Component("comb_device")
    layer = (1, 0)

    # 1. Main body
    # Dimensions: 25um width, 5um height
    # With centered=True, Top edge is at Y = 2.5, Bottom edge is at Y = -2.5
    rect_width = 25.0
    rect_height = 5.0
    body = c << gf.components.rectangle(size=(rect_width, rect_height), layer=layer, centered=True)

    # 2. Top Fingers (4 identical structures)
    f_w_base = 2.0
    f_w_top = 1.0
    f_taper_len = 2.5
    f_straight_len = 1.5
    
    xs_straight = gf.cross_section.cross_section(width=f_w_top, layer=layer)

    @gf.cell
    def top_finger():
        fc = gf.Component("top_finger")
        taper = fc << gf.components.taper(length=f_taper_len, width1=f_w_base, width2=f_w_top, layer=layer)
        straight = fc << gf.components.straight(length=f_straight_len, cross_section=xs_straight)
        
        # Connect the straight section to the narrow end of the taper
        straight.connect("o1", taper.ports["o2"])
        return fc

    finger_comp = top_finger()

    # Group the fingers towards the center instead of spreading them to the far edges
    x_positions = [-7.5, -2.5, 2.5, 7.5]
    for x in x_positions:
        f_ref = c << finger_comp
        f_ref.rotate(90) # Point upwards
        f_ref.move((x, 2.5)) # Attach base exactly to the top edge of the body (Y=2.5)

    # 3. Bottom Finger
    # A single, stubby taper pointing downwards
    b_len = 1.0
    b_w_base = 1.5
    b_w_tip = 0.5
    b_finger = c << gf.components.taper(length=b_len, width1=b_w_base, width2=b_w_tip, layer=layer)
    
    b_finger.rotate(-90) # Point downwards
    b_finger.move((0, -2.5)) # Attach base exactly to the bottom edge of the body (Y=-2.5)

    return c

if __name__ == "__main__":
    c = device()
    # Required: output to a GDS file
    c.write_gds("device.gds")