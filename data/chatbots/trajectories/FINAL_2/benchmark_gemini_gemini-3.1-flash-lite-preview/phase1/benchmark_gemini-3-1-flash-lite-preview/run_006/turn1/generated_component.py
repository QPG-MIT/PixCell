import gdsfactory as gf

@gf.cell
def device_with_fingers():
    """
    Constructs the device geometry using primitives from the catalog.
    """
    c = gf.Component("my_device")
    
    # Layer definition
    layer = (1, 0)
    
    # 1. Create the central body (Rectangle)
    # Dimensions: 25um x 4um
    body = c << gf.components.rectangle(size=(25, 4), layer=layer, centered=True)
    
    # 2. Create the Fingers (Tapers)
    # Length of finger is 3um to meet the 10um total footprint (3+4+3=10)
    def create_finger():
        # Using a taper primitive
        return gf.components.taper(length=3, width1=2, width2=1, layer=layer)
    
    # Add 4 Top Fingers
    # Positions relative to center of body
    x_positions = [-9, -3, 3, 9] 
    for x in x_positions:
        finger = c << create_finger()
        finger.rotate(90) # Point upwards
        # Move: Body height is 4 (y range -2 to 2). 
        # Move finger to align the wide end at y=2.
        # Since taper origin is at its center, we shift by length/2
        finger.move((x, 2 + 1.5)) 
        
    # Add 1 Bottom Finger
    bottom_finger = c << create_finger()
    bottom_finger.rotate(-90) # Point downwards
    bottom_finger.move((0, -2 - 1.5))
    
    # 3. Flatten
    # This merges all references into one polygon structure.
    c.flatten()
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = device_with_fingers()
    
    # Show the device (KLayout)
    device.show() 
    
    # Explicitly write the GDS file
    gds_path = device.write_gds("my_device.gds")
    print(f"GDS file successfully produced at: {gds_path}")