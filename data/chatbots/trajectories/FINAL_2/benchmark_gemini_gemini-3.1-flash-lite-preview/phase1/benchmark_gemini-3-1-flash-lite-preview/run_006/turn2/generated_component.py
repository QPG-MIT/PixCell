import gdsfactory as gf

@gf.cell
def device_with_fingers():
    """
    Recreates the device by overlapping the fingers into the body 
    to ensure a clean union of the geometry.
    """
    c = gf.Component("my_device")
    
    # Layer definition
    layer = (1, 0)
    
    # 1. Create the central body (Rectangle)
    # Dimensions: 25um x 4um
    body = c << gf.components.rectangle(size=(25, 4), layer=layer, centered=True)
    
    # 2. Create the Fingers (Tapers)
    # We define a function for the taper
    def create_finger():
        # Using a taper primitive
        # Finger length is 3um
        return gf.components.taper(length=3, width1=2, width2=1, layer=layer)
    
    # The fingers need to overlap with the rectangle to form one polygon.
    # We "bury" them 0.5um into the body.
    overlap = 0.5
    
    # Add 4 Top Fingers
    # Positions relative to center
    x_positions = [-9, -3, 3, 9] 
    for x in x_positions:
        finger = c << create_finger()
        finger.rotate(90) # Point upwards
        # y-position: Start at edge (2) + half-length of taper (1.5) - overlap (0.5)
        # = 3.0
        finger.move((x, 3.0)) 
        
    # Add 1 Bottom Finger
    bottom_finger = c << create_finger()
    bottom_finger.rotate(-90) # Point downwards
    # y-position: Start at edge (-2) - half-length of taper (1.5) + overlap (0.5)
    # = -3.0
    bottom_finger.move((0, -3.0))
    
    # 3. Flatten and Save
    # Flattening combines all overlapping objects into a single polygon
    c.flatten()
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = device_with_fingers()
    
    # Save the GDS
    gds_path = device.write_gds("final_device.gds")
    print(f"GDS file successfully produced at: {gds_path}")
    
    # Show the device (KLayout)
    device.show()