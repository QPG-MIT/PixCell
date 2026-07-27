import gdsfactory as gf

@gf.cell
def racetrack_device():
    c = gf.Component()
    
    # 1. Define custom cross-section compatible with the footprint
    # Explicitly setting radius=0.5 allows us to use small bends 
    # without triggering the min_bend_radius error.
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0), radius=0.5)
    
    # 2. Geometry Parameters
    r = 0.5
    straight_len = 1.5
    gap = 1.0
    
    # 3. Create Primitives
    # Two horizontal straight waveguides
    top_wg = c << gf.components.straight(length=straight_len, cross_section=xs)
    bot_wg = c << gf.components.straight(length=straight_len, cross_section=xs)
    
    # Four bends to create the racetrack turns (2 on left, 2 on right)
    # Using bend_circular for simple, tight turns
    bl_top = c << gf.components.bend_circular(radius=r, angle=90, cross_section=xs)
    bl_bot = c << gf.components.bend_circular(radius=r, angle=90, cross_section=xs)
    br_top = c << gf.components.bend_circular(radius=r, angle=90, cross_section=xs)
    br_bot = c << gf.components.bend_circular(radius=r, angle=90, cross_section=xs)
    
    # 4. Assemble the Racetrack Loop
    # Position straight rails vertically
    top_wg.movey(gap / 2)
    bot_wg.movey(-gap / 2)
    
    # Connect Left side turns
    # Connect bend output to straight input
    bl_top.connect("o2", top_wg.ports["o1"])
    bl_bot.connect("o2", bot_wg.ports["o1"])
    # Connect the two left bends to close the loop
    bl_top.connect("o1", bl_bot.ports["o1"])
    
    # Connect Right side turns
    br_top.connect("o1", top_wg.ports["o2"])
    br_bot.connect("o1", bot_wg.ports["o2"])
    # Connect the two right bends to close the loop
    br_top.connect("o2", br_bot.ports["o2"])
    
    # 5. Add Internal Rectangles
    # Placing them in the middle of the straight sections
    rect = gf.components.rectangle(size=(0.5, 0.8), layer=(1, 0), centered=True)
    
    # Position rectangles at (0, y_offset)
    r1 = c << rect
    r1.movey(gap / 2)
    
    r2 = c << rect
    r2.movey(-gap / 2)
    
    return c

# Generate and save
device = racetrack_device()
device.write_gds("racetrack_device.gds")