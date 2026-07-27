import gdsfactory as gf

@gf.cell
def custom_device_assembly():
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Main rectangular body
    # Using 'c <<' to create a reference in the assembly
    rect = gf.components.rectangle(size=(25, 4), layer=layer, centered=True)
    c << rect
    
    # 2. Define the Taper (finger)
    # The taper creates the trapezoidal shape seen in your reference
    taper_comp = gf.components.taper(length=3, width1=2.5, width2=0.8, layer=layer)
    
    # 3. Add Top Fingers
    # The rectangle y-range is -2 to 2 (height 4 centered at 0).
    # We place the taper so its base aligns with the top edge (y=2).
    # Since the taper is centered, we rotate and move it to position.
    for x_pos in [-9, -3, 3, 9]:
        finger = c << taper_comp
        finger.rotate(90)
        # Position: The center of the taper is (1.5, 0) relative to its origin.
        # Moving to (x_pos, 2 + 1.5) puts the base at y=2.
        finger.move((x_pos, 3.5))
        
    # 4. Add Bottom Finger
    bottom_finger = c << taper_comp
    bottom_finger.rotate(-90)
    # Moving to (0, -2 - 1.5) puts the base at y=-2.
    bottom_finger.move((0, -3.5))
    
    return c

if __name__ == "__main__":
    device = custom_device_assembly()
    device.write_gds("custom_device.gds")