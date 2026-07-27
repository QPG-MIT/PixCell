import gdsfactory as gf

@gf.cell
def mmi_1x4_splitter():
    c = gf.Component("mmi_1x4_device")
    
    # 1. Main Body
    # Create the central rectangular footprint constraint (25um x 10um)
    # By default, gf.components.rectangle puts the lower-left corner at (0,0).
    body = c << gf.components.rectangle(size=(25.0, 10.0), layer=(1, 0))
    
    # Move it so its center is exactly at (0,0)
    # This places the top edge at Y = 5.0 and the bottom edge at Y = -5.0
    body.move((-12.5, -5.0))

    # 2. Output Arms (Top)
    # We want 4 evenly spaced ports along the top edge
    pitch = 25.0 / 4.0
    x_centers = [(-12.5 + pitch / 2) + i * pitch for i in range(4)]
    
    for x in x_centers:
        # Taper section attached to the main body
        # width1 is the wide base touching the body, width2 is the output tip
        arm_taper = c << gf.components.taper(length=8.0, width1=5.0, width2=2.5)
        
        # Default taper 'o1' faces West (180 deg).
        # Rotating +90 degrees makes it face South (270 deg) so the geometry builds upwards (+Y).
        arm_taper.rotate(90) 
        
        # Move the newly facing 'o1' base exactly to the top edge of the MMI body
        arm_taper.move((x, 5.0))
        
        # Straight section
        # Created using a straight taper (equal widths) for maximum layout robustness
        arm_straight = c << gf.components.taper(length=12.0, width1=2.5, width2=2.5)
        
        # Connect the straight section securely to the tip of the taper
        arm_straight.connect("o1", arm_taper.ports["o2"])

    # 3. Input Arm (Bottom)
    # Single centralized taper feeding into the bottom edge
    in_taper = c << gf.components.taper(length=8.0, width1=6.0, width2=2.5)
    
    # Rotating -90 degrees makes the base 'o1' face North (90 deg) so the geometry builds downwards (-Y).
    in_taper.rotate(-90)
    
    # Move the wide base port exactly to the center bottom edge of the MMI body
    in_taper.move((0.0, -5.0))

    return c

if __name__ == "__main__":
    # Instantiate the assembled device
    device = mmi_1x4_splitter()
    
    # Output perfectly flat parametric construction to standard file
    device.write_gds("mmi_1x4.gds")