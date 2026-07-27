import gdsfactory as gf

@gf.cell
def custom_device():
    c = gf.Component()
    
    # 1. Main body: 25x4 rectangle, centered at (0,0)
    # The y-range is thus from -2 to 2, and x-range from -12.5 to 12.5.
    rect = c << gf.components.rectangle(size=(25, 4), centered=True, layer=(1, 0))
    
    # 2. Define the Taper (finger)
    # Using length 2.5 and widths 1.8 (base) to 0.8 (tip)
    taper = gf.components.taper(length=2.5, width1=1.8, width2=0.8, layer=(1, 0))
    
    # 3. Add Top Fingers
    # The top edge is at y = 2.
    # Rotating around (0,0) ensures the taper's port (o1) remains at (0,0)
    # before we move it to the final position.
    for x_pos in [-9, -3, 3, 9]:
        finger = c << taper
        finger.rotate(90, center=(0, 0))
        # Move so the base of the taper is flush with the rectangle's top edge
        finger.move((x_pos, 2))
        
    # 4. Add Bottom Finger
    # The bottom edge is at y = -2.
    bottom_finger = c << taper
    # Rotate -90 degrees to point downwards
    bottom_finger.rotate(-90, center=(0, 0))
    # Move so the base of the taper is flush with the rectangle's bottom edge
    bottom_finger.move((0, -2))
    
    return c

if __name__ == "__main__":
    device = custom_device()
    device.write_gds("custom_device.gds")