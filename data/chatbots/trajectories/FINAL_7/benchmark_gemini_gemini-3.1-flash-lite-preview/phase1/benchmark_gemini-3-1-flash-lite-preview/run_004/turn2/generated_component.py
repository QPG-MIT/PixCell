import gdsfactory as gf

@gf.cell
def racetrack_resonator():
    c = gf.Component()
    
    # 1. Define Cross Section (must match the footprint constraints)
    # Footprint is [3.0, 5.5]. Bend radius = 1.5. Width = 0.4.
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))

    # 2. Build the Outer Loop using Path
    # Stadium shape: 2 straights (2.5um) + 4 arcs (radius 1.5um)
    p = gf.Path()
    p.append(gf.path.straight(length=2.5))
    p.append(gf.path.euler(radius=1.5, angle=90))
    p.append(gf.path.straight(length=0.001)) # Short transition to close loop
    p.append(gf.path.euler(radius=1.5, angle=90))
    p.append(gf.path.straight(length=2.5))
    p.append(gf.path.euler(radius=1.5, angle=90))
    p.append(gf.path.straight(length=0.001))
    p.append(gf.path.euler(radius=1.5, angle=90))
    
    # Extrude the path into the actual component
    loop = gf.path.extrude(p, cross_section=xs)
    c << loop

    # 3. Add Inner Features
    # The two horizontal bars
    bar_size = (1.5, 0.4)
    # Positions are centered at (0, 0)
    # Top bar
    bar_top = c << gf.components.rectangle(size=bar_size, layer=(1, 0), centered=True)
    bar_top.movey(0.4)
    
    # Bottom bar
    bar_bot = c << gf.components.rectangle(size=bar_size, layer=(1, 0), centered=True)
    bar_bot.movey(-0.4)
    
    # 4. Add the Connecting Arms
    # These vertical bridge pieces connect the inner bars to the outer loop
    arm_size = (0.2, 0.3)
    
    # We place 4 of them
    for x_pos in [-0.4, 0.4]:
        for y_pos in [-0.25, 0.25]:
            arm = c << gf.components.rectangle(size=arm_size, layer=(1, 0), centered=True)
            arm.move((x_pos, y_pos))

    return c

# Create and save
device = racetrack_resonator()
device.write_gds("racetrack_resonator.gds")