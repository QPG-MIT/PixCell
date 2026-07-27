import gdsfactory as gf

@gf.cell
def custom_racetrack_device():
    c = gf.Component()
    
    # 1. Custom cross_section to allow small bend radius
    # radius_min must be <= bend_radius
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0), radius_min=0.1)

    # 2. Dimensions based on footprint [3.0, 5.5]
    # Height = 3.0 -> Bend Radius = 1.5
    # Width = 5.5 -> Straight length = 5.5 - (2 * 1.5) = 2.5
    bend_rad = 1.5
    straight_len = 2.5

    # 3. Build Outer Loop (assign to variables first)
    top = c << gf.components.straight(length=straight_len, cross_section=xs)
    bot = c << gf.components.straight(length=straight_len, cross_section=xs)
    b1 = c << gf.components.bend_euler(radius=bend_rad, angle=90, cross_section=xs)
    b2 = c << gf.components.bend_euler(radius=bend_rad, angle=90, cross_section=xs)
    b3 = c << gf.components.bend_euler(radius=bend_rad, angle=90, cross_section=xs)
    b4 = c << gf.components.bend_euler(radius=bend_rad, angle=90, cross_section=xs)

    # Assemble outer ring
    b1.connect("o1", top.ports["o2"])
    bot.connect("o1", b1.ports["o2"])
    b2.connect("o1", bot.ports["o2"])
    top.connect("o1", b2.ports["o2"])

    # 4. Build Inner Bars (assign to variable, then move)
    rect_size = (1.5, 0.4)
    r1 = c << gf.components.rectangle(size=rect_size, layer=(1, 0), centered=True)
    r2 = c << gf.components.rectangle(size=rect_size, layer=(1, 0), centered=True)
    
    r1.movey(0.4)
    r2.movey(-0.4)

    # 5. Build Connecting Arms (assign to variable, then move)
    # These connect the bars to the outer loop
    conn_size = (0.2, 0.3)
    
    # Create and move 4 connectors
    c1 = c << gf.components.rectangle(size=conn_size, layer=(1, 0), centered=True)
    c1.move((0.4, 0.25))
    
    c2 = c << gf.components.rectangle(size=conn_size, layer=(1, 0), centered=True)
    c2.move((-0.4, 0.25))
    
    c3 = c << gf.components.rectangle(size=conn_size, layer=(1, 0), centered=True)
    c3.move((0.4, -0.25))
    
    c4 = c << gf.components.rectangle(size=conn_size, layer=(1, 0), centered=True)
    c4.move((-0.4, -0.25))
    
    return c

# Create and save
device = custom_racetrack_device()
device.write_gds("custom_device.gds")