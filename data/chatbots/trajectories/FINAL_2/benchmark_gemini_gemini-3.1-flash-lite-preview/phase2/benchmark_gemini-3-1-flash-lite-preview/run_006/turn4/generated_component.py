import gdsfactory as gf

@gf.cell
def device_with_fingers():
    """
    Creates the device using a central rectangle and tapered 
    protrusions for the fingers.
    """
    c = gf.Component("my_device")
    
    # Layer definition
    layer = (1, 0)
    
    # 1. Create the central body (Rectangle)
    # Dimensions: 25um x 10um
    body = c << gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    
    # 2. Define the Taper parameters
    taper_len = 6.0
    width_base = 3.0
    width_tip = 1.5
    
    def create_taper():
        return gf.components.taper(
            length=taper_len, 
            width1=width_base, 
            width2=width_tip, 
            layer=layer
        )
    
    # 3. Add 4 Top Fingers
    x_positions = [-9, -3, 3, 9] 
    for x in x_positions:
        finger = c << create_taper()
        finger.rotate(90)
        # Position: The base of the taper (width1) is at y=5 (the top edge of the body).
        # We offset by length/2 because the taper is centered.
        finger.move((x, 5 + taper_len / 2))
        
    # 4. Add 1 Bottom Finger
    bottom_finger = c << create_taper()
    bottom_finger.rotate(-90)
    # Position: The base sits at y=-5 (the bottom edge of the body).
    bottom_finger.move((0, -5 - taper_len / 2))
    
    # Do not reassign c to c.flatten() as flatten() returns None.
    # The overlapping shapes will render correctly as one object in the GDS.
    c.flatten()
    
    return c

if __name__ == "__main__":
    device = device_with_fingers()
    
    # Save the GDS
    gds_path = device.write_gds("final_device.gds")
    print(f"GDS file successfully produced at: {gds_path}")
    
    # Show the device
    device.show()