import gdsfactory as gf

@gf.cell
def custom_device():
    c = gf.Component()
    
    # 1. Main body: 25x6 rectangle, centered at (0,0)
    # The y-range is from -3 to 3.
    rect = c << gf.components.rectangle(size=(25, 6), centered=True, layer=(1, 0))
    
    # 2. Define the Taper (finger)
    # Using length 2.0 and widths 1.8 (base) to 0.8 (tip)
    taper = gf.components.taper(length=2.0, width1=1.8, width2=0.8, layer=(1, 0))
    
    # 3. Add Top Fingers
    # The top edge is at y = 3.
    # The fingers are placed at x = -9, -3, 3, 9 for a symmetric distribution
    for x_pos in [-9, -3, 3, 9]:
        finger = c << taper
        finger.rotate(90, center=(0, 0))
        # Moving to (x_pos, 3) places the finger base on the top edge
        finger.move((x_pos, 3))
        
    # 4. Add Bottom Finger (single, centered)
    # The bottom edge is at y = -3.
    bottom_finger = c << taper
    bottom_finger.rotate(-90, center=(0, 0))
    # Moving to (0, -3) places the finger base on the bottom edge center
    bottom_finger.move((0, -3))
    
    return c

if __name__ == "__main__":
    device = custom_device()
    device.write_gds("custom_device.gds")