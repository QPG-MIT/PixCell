import gdsfactory as gf

@gf.cell
def device_with_fingers():
    """
    Creates the device using rectangles for the body and fingers 
    to match the target geometry.
    """
    c = gf.Component("my_device")
    
    # Layer definition
    layer = (1, 0)
    
    # 1. Create the central body (Rectangle)
    # Dimensions: 25um x 10um (based on footprint constraint)
    # Centered at (0,0) so the top edge is at y=5 and bottom at y=-5
    body = c << gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    
    # 2. Create the Fingers (Rectangles)
    # The fingers appear to be rectangular, not tapered.
    # We create a function to generate these rectangles.
    def create_finger():
        # Adjust dimensions to match the visual aspect ratio of the target
        return gf.components.rectangle(size=(2, 6), layer=layer, centered=True)
    
    # Add 4 Top Fingers
    # We want them placed along the top edge of the body
    x_positions = [-9, -3, 3, 9] 
    for x in x_positions:
        finger = c << create_finger()
        # The body top edge is at y=5. 
        # Since the finger is 6um tall (centered), its center needs to be at 
        # y = 5 + (6/2) = 8um to sit flush on top.
        finger.move((x, 8)) 
        
    # Add 1 Bottom Finger
    bottom_finger = c << create_finger()
    # The body bottom edge is at y=-5.
    # Its center needs to be at y = -5 - (6/2) = -8um to sit flush below.
    bottom_finger.move((0, -8))
    
    # 3. Flatten
    # Merges all rectangles into one contiguous polygon shape
    c.flatten()
    
    return c

if __name__ == "__main__":
    device = device_with_fingers()
    
    # Save the GDS
    gds_path = device.write_gds("final_device.gds")
    print(f"GDS file successfully produced at: {gds_path}")
    
    # Show the device
    device.show()