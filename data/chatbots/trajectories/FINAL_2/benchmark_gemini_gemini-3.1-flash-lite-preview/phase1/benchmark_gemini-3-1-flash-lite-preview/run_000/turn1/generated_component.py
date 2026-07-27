import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the device by composing primitives and using Boolean operations 
    to merge them into a single structure.
    """
    # 1. Define Parameters
    layer = (1, 0)
    body_size = (22, 5)
    pin_size = (2, 3)
    
    # 2. Create base primitives
    body = gf.components.rectangle(size=body_size, layer=layer)
    pin = gf.components.rectangle(size=pin_size, layer=layer)
    
    # 3. Helper to create a positioned pin component
    def create_positioned_pin(x, y):
        comp = gf.Component()
        ref = comp << pin
        ref.move((x - pin_size[0]/2, y - pin_size[1]/2))
        return comp

    # 4. Perform Boolean Operations to merge geometry
    # We initialize the 'result' with the main body
    result = body
    
    # Define pin locations (relative to center of body)
    # 4 top pins, 1 bottom pin
    top_pins_x = [-9, -3, 3, 9]
    top_y = body_size[1]/2 + pin_size[1]/2
    bot_y = -body_size[1]/2 - pin_size[1]/2
    
    # Add top pins
    for x in top_pins_x:
        temp_pin = create_positioned_pin(x, top_y)
        result = gf.boolean(result, temp_pin, operation="or", layer=layer)
        
    # Add bottom pin
    temp_bot_pin = create_positioned_pin(0, bot_y)
    result = gf.boolean(result, temp_bot_pin, operation="or", layer=layer)
    
    return result

# 5. Generate and save
if __name__ == "__main__":
    device = create_device()
    
    # Save the file explicitly
    device.write_gds("device_layout.gds")
    
    # Visualize
    device.show()
    print("GDS file 'device_layout.gds' successfully produced.")