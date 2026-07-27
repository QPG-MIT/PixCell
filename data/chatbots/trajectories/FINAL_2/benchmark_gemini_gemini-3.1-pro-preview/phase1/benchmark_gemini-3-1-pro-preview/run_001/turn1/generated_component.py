import gdsfactory as gf

@gf.cell
def device():
    """
    Creates the comb-like geometry using parametric primitives.
    The device fits exactly within the specified [25, 10] footprint.
    """
    c = gf.Component("comb_device")
    layer = (1, 0)

    # 1. Main rectangular body
    # Dimensions: 25um width, 4.5um height
    # Shifted down by 1.25 to leave 4um on top for fingers and 1.5um below.
    # Top edge will be at Y = 1.0, Bottom edge at Y = -3.5
    rect_width = 25.0
    rect_height = 4.5
    body = c << gf.components.rectangle(size=(rect_width, rect_height), layer=layer, centered=True)
    body.move((0, -1.25))

    # Cross section for straight parts of fingers
    f_w_top = 0.8
    xs_straight = gf.cross_section.cross_section(width=f_w_top, layer=layer)

    # 2. Top Fingers (4 identical structures)
    # Define a sub-component for reusability
    @gf.cell
    def top_finger():
        fc = gf.Component("top_finger")
        f_taper_len = 2.5
        f_straight_len = 1.5
        f_w_base = 2.0
        
        taper = fc << gf.components.taper(length=f_taper_len, width1=f_w_base, width2=f_w_top, layer=layer)
        straight = fc << gf.components.straight(length=f_straight_len, cross_section=xs_straight)
        
        # Connect the straight section to the narrow end of the taper
        straight.connect("o1", taper.ports["o2"])
        return fc

    finger_comp = top_finger()

    # Place the 4 fingers evenly spaced across the top
    spacing = rect_width / 4.0
    start_x = -rect_width / 2.0 + spacing / 2.0
    for i in range(4):
        f_ref = c << finger_comp
        f_ref.rotate(90) # Point upwards
        x = start_x + i * spacing
        f_ref.move((x, 1.0)) # Attach base exactly to the top edge of the body

    # 3. Bottom Finger
    b_len = 1.5
    b_w_base = 2.0
    b_w_tip = 0.8
    b_finger = c << gf.components.taper(length=b_len, width1=b_w_base, width2=b_w_tip, layer=layer)
    
    b_finger.rotate(-90) # Point downwards
    b_finger.move((0, -3.5)) # Attach base exactly to the bottom edge of the body

    return c

if __name__ == "__main__":
    c = device()
    # Required: output to a GDS file
    c.write_gds("device.gds")