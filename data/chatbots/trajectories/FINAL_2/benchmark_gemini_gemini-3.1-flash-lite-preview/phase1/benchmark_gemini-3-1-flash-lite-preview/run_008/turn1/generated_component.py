import gdsfactory as gf

@gf.cell
def custom_device():
    c = gf.Component()
    
    # 1. Define dimensions based on the 25x10 footprint
    # Main body: 22um width, 4um height
    # Fingers: 2um width, 3um height
    # Total Height = 3 (top) + 4 (body) + 3 (bottom) = 10um
    
    body_size = (22, 4)
    finger_size = (2, 3)
    
    # 2. Create Primitives
    main_body = gf.components.rectangle(size=body_size, centered=True, layer=(1, 0))
    finger_top = gf.components.rectangle(size=finger_size, centered=True, layer=(1, 0))
    finger_bot = gf.components.rectangle(size=finger_size, centered=True, layer=(1, 0))
    
    # 3. Add Main Body
    body_ref = c << main_body
    
    # 4. Add 4 Fingers on Top
    # Body extends to y=2 (top edge) and y=-2 (bottom edge)
    # Fingers need to be centered at y = 2 + (height/2) = 2 + 1.5 = 3.5
    top_y = 3.5
    top_x_positions = [-7.5, -2.5, 2.5, 7.5]
    
    for x in top_x_positions:
        f = c << finger_top
        f.move((x, top_y))
        
    # 5. Add 1 Finger on Bottom
    # Finger needs to be centered at y = -2 - (height/2) = -2 - 1.5 = -3.5
    bot_y = -3.5
    
    f_bot = c << finger_bot
    f_bot.move((0, bot_y))
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device = custom_device()
    device.show() # Opens in KLayout
    device.write_gds("custom_device.gds")