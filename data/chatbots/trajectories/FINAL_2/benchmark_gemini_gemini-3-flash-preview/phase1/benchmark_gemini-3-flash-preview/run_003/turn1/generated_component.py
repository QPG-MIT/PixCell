import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the device geometry using parametric primitives.
    Uses .ports["name"].center to avoid subscripting errors with DPort objects.
    """
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # 1. Main Body Rectangle (25um x 5um)
    rect_w = 25.0
    rect_h = 5.0
    rect_ref = c << gf.components.rectangle(size=(rect_w, rect_h), layer=layer)
    # Move the rectangle so its center is at (0, 0)
    # rectangle (0,0) is bottom-left, so we move it by half dimensions
    rect_ref.move(destination=(-rect_w / 2, -rect_h / 2))
    
    # 2. Top Fingers (4 units)
    f_straight_l = 2.0
    f_taper_l = 1.5
    f_w_narrow = 1.2
    f_w_wide = 2.4
    
    def make_finger():
        f = gf.Component()
        # Create Taper: width1 is base (wide), width2 is tip (narrow)
        taper = f << gf.components.taper(
            length=f_taper_l, width1=f_w_wide, width2=f_w_narrow, layer=layer
        )
        # Create Straight segment
        straight = f << gf.components.straight(
            length=f_straight_l, 
            cross_section=gf.cross_section.cross_section(width=f_w_narrow, layer=layer)
        )
        # Connect straight to taper. 
        # Using .ports["name"] is explicit and robust.
        straight.connect("o1", taper.ports["o2"])
        
        # Expose the wide base port for external connection logic
        f.add_port("base", port=taper.ports["o1"])
        return f

    # Place 4 fingers along the top edge of the main body
    x_positions = [-9.0, -3.0, 3.0, 9.0]
    for x in x_positions:
        f_ref = c << make_finger()
        f_ref.rotate(90) # Point fingers upward
        
        # We use .center to pass a coordinate tuple to move(), 
        # avoiding the 'DPort is not subscriptable' error.
        f_ref.move(origin=f_ref.ports["base"].center, destination=(x, rect_h / 2))

    # 3. Bottom Protrusion (Single Taper)
    bot_taper_l = 1.5
    bot_w_top = 2.8
    bot_w_bot = 1.4
    
    bot_taper = c << gf.components.taper(
        length=bot_taper_l, width1=bot_w_top, width2=bot_w_bot, layer=layer
    )
    bot_taper.rotate(-90) # Point taper downward
    
    # Align the top of the taper (o1) to the center-bottom of the body
    bot_taper.move(origin=bot_taper.ports["o1"].center, destination=(0, -rect_h / 2))

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreated_device()
    
    # Save the output to a GDS file
    device.write_gds("recreated_device.gds")
    
    # To visualize (requires a viewer like KLayout):
    # device.show()