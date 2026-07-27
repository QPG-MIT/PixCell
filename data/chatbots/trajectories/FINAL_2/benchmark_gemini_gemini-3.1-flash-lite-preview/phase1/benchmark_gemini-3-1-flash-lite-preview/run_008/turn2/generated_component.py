import gdsfactory as gf

@gf.cell
def tapered_device():
    c = gf.Component()
    
    # 1. Define dimensions
    # Total footprint fits within 25um x 10um
    body_size = (20, 4)
    finger_length = 3
    
    # 2. Define Primitives
    # Main block
    body = c << gf.components.rectangle(size=body_size, centered=True, layer=(1, 0))
    
    # Top fingers: 4 tapered bars
    # width1 is the base (touching body), width2 is the tip
    top_taper = gf.components.taper(length=finger_length, width1=3, width2=1.5)
    
    # Bottom finger: 1 larger tapered bar
    bot_taper = gf.components.taper(length=finger_length, width1=5, width2=2.5)
    
    # 3. Position Top Fingers
    # The body extends to y=2 (top edge)
    top_y_origin = 2
    top_x_positions = [-7.5, -2.5, 2.5, 7.5]
    
    for x in top_x_positions:
        t = c << top_taper
        # Rotate 90 degrees to point upwards
        t.rotate(90)
        # Align the base of the taper (which is now at the bottom of the component) 
        # to the top edge of the body
        t.move((x, top_y_origin))
        
    # 4. Position Bottom Finger
    # Body bottom edge is at y = -2
    bot_taper_ref = c << bot_taper
    # Rotate -90 degrees to point downwards
    bot_taper_ref.rotate(-90)
    # Align the base of the taper (which is now at the top of the component) 
    # to the bottom edge of the body
    bot_taper_ref.move((0, -2))
    
    return c

# Generate and save
if __name__ == "__main__":
    device = tapered_device()
    device.show()
    device.write_gds("tapered_device.gds")