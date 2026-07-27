import gdsfactory as gf

@gf.cell
def chain_link_device():
    c = gf.Component()
    
    # CORRECT WAY to define cross_section:
    # Use the factory function, not the class constructor.
    # We set a small radius (0.1) to allow tight bending without errors.
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0), radius=0.1)

    # 1. Racetrack Geometry (The Loop)
    # Total width constraint = 3.0um. 
    # Radius = 1.25 (to keep outer width ~3.0um including line width)
    # Total height constraint = 5.5um.
    # Straight length = 5.5 - (2 * radius) = 3.0um
    r = 1.25
    s_len = 3.0
    
    # Build path
    p = gf.Path()
    p.append(gf.path.arc(radius=r, angle=180))
    p.append(gf.path.straight(length=s_len))
    p.append(gf.path.arc(radius=r, angle=180))
    p.append(gf.path.straight(length=s_len))
    
    # Extrude path
    loop = c << gf.path.extrude(p, cross_section=xs)

    # 2. Internal Blocks
    # Using simple rectangle components centered in the loop
    block = gf.components.rectangle(size=(0.8, 0.6), layer=(1, 0), centered=True)
    
    b1 = c << block
    b1.movey(0.7) 
    
    b2 = c << block
    b2.movey(-0.7)

    # 3. Connector Arms
    # Rectangles connecting blocks to the inner wall
    arm = gf.components.rectangle(size=(0.5, 0.3), layer=(1, 0), centered=True)
    
    # Place arms on both sides of the blocks
    for y_pos in [0.7, -0.7]:
        for x_dir in [-1, 1]:
            arm_ref = c << arm
            arm_ref.move((x_dir * 0.7, y_pos))

    return c

# Generate and save
device = chain_link_device()
device.write_gds("chain_link_final.gds")