import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the device geometry composed of a main rectangle 
    and tapered pillars.
    """
    c = gf.Component("my_device")
    
    # 1. Define the main central block
    # Using a rectangle primitive, centered at (0,0)
    # Footprint of device is 25x10. Let's make main block 25x4.
    main_box = c << gf.components.rectangle(size=(25, 4), layer=(1, 0), centered=True)
    
    # 2. Define the tapered pillar geometry
    # We use the 'taper' function which creates a trapezoid
    # Top pillars (height = 3)
    top_taper = gf.components.taper(length=3, width1=3, width2=2)
    
    # Bottom pillar (height = 2)
    bottom_taper = gf.components.taper(length=2, width1=4, width2=2)
    
    # 3. Add and place Top Pillars
    # The box is 4 units high, extending from y = -2 to y = 2.
    # We want the pillars to start at y = 2.
    # The taper is length 3, so its center is offset by 1.5 units when rotated.
    # Placement Y = 2 (top edge) + 1.5 (half-length) = 3.5
    top_positions = [-9, -3, 3, 9]
    for x_pos in top_positions:
        t = c << top_taper
        t.rotate(90)
        t.move((x_pos, 3.5))
        
    # 4. Add and place Bottom Pillar
    # The box bottom edge is at y = -2.
    # The taper is length 2, center offset 1.
    # Placement Y = -2 - 1 = -3
    b = c << bottom_taper
    b.rotate(-90)
    b.move((0, -3))
    
    return c

# Generate and save the device
device = create_device()
device.write_gds("device.gds")

# Optional: Visualize the layout
# device.show()