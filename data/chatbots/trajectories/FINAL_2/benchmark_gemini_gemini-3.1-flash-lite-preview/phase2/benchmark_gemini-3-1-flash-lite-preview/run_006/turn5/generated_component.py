import gdsfactory as gf

@gf.cell
def device_with_fingers():
    """
    Creates the device using a boolean 'or' operation to merge the 
    central rectangle and tapered fingers into a single silhouette.
    """
    c = gf.Component("my_device")
    layer = (1, 0)
    
    # 1. Create the central body (Rectangle)
    # Dimensions: 25um x 10um
    body = gf.components.rectangle(size=(25, 10), layer=layer, centered=True)
    
    # 2. Define the Taper
    taper = gf.components.taper(length=6.0, width1=3.0, width2=1.5, layer=layer)
    
    # 3. Create a temporary container for the fingers to position them
    fingers = gf.Component("fingers_container")
    
    # Add 4 Top Fingers
    # The body extends to y=5. Taper is 6um long (centered).
    # To place the base at y=5, we position the center of the taper at y = 5 + (6/2) = 8.
    for x in [-9, -3, 3, 9]:
        f = fingers << taper
        f.rotate(90)
        f.move((x, 8))
        
    # Add 1 Bottom Finger
    # To place the base at y=-5, we position the center of the taper at y = -5 - (6/2) = -8.
    f = fingers << taper
    f.rotate(-90)
    f.move((0, -8))
        
    # 4. Perform Boolean Union
    # This merges the body and the fingers into one single, clean polygon,
    # effectively removing the internal overlap lines.
    merged_device = gf.boolean(body, fingers, operation="or", layer=layer)
    
    # Add the result to our main component
    c << merged_device
    
    return c

if __name__ == "__main__":
    device = device_with_fingers()
    
    # Save the GDS
    gds_path = device.write_gds("final_device.gds")
    print(f"GDS file successfully produced at: {gds_path}")
    
    # Show the device
    device.show()