import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the device by composing tapered pins on a central body 
    and performing a boolean union to merge them into a single geometry.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define dimensions
    # Body is 25um wide by 5um tall
    body_width = 25
    body_height = 5
    
    # Pin dimensions
    pin_len = 2.5
    pin_width_base = 2.5
    pin_width_tip = 1.0
    
    # 2. Create Primitives
    # Body
    body = gf.components.rectangle(size=(body_width, body_height), layer=layer)
    
    # Tapered Pin
    # We use a taper primitive which creates the trapezoidal shape
    pin = gf.components.taper(
        length=pin_len, 
        width1=pin_width_base, 
        width2=pin_width_tip, 
        layer=layer
    )
    
    # 3. Create a temporary container for all pins
    # This keeps our alignment math clean before the boolean operation
    all_pins = gf.Component()
    
    # Add 4 Top Pins
    # We place them at specific x coordinates along the top edge
    top_pins_x = [-9, -3, 3, 9]
    for x in top_pins_x:
        p_ref = all_pins << pin
        p_ref.rotate(90)
        # Position: X = offset, Y = half-body height + half-pin length
        p_ref.move((x, body_height / 2 + pin_len / 2))
        
    # Add 1 Bottom Pin
    p_bot = all_pins << pin
    p_bot.rotate(-90)
    # Position: X = 0, Y = -(half-body height + half-pin length)
    p_bot.move((0, -(body_height / 2 + pin_len / 2)))
    
    # 4. Boolean Operation
    # We merge the body and the pin container into one single polygon set
    merged_device = gf.boolean(body, all_pins, operation="or", layer=layer)
    
    # Add the merged geometry to our final component
    c.add_ref(merged_device)
    
    return c

# Execute and save
if __name__ == "__main__":
    device = create_device()
    device.write_gds("device_layout.gds")
    device.show()