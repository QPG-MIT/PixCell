import gdsfactory as gf

@gf.cell
def chain_link_device():
    c = gf.Component()
    
    # 1. Define Cross-section
    # Using a 0.3um width for the outer loop to keep it clean
    xs = gf.cross_section.cross_section(width=0.3, layer=(1, 0))

    # 2. Construct the Outer Loop
    # Footprint: 3.0um width -> Radius = 1.5um
    # Total height 5.5um -> Straight segment = 5.5 - (2 * 1.5) = 2.5um
    p = gf.Path()
    # Create the loop path
    p.append(gf.path.arc(radius=1.5, angle=180))
    p.append(gf.path.straight(length=2.5))
    p.append(gf.path.arc(radius=1.5, angle=180))
    p.append(gf.path.straight(length=2.5))
    
    # Extrude and add to component
    loop = c << gf.path.extrude(p, cross_section=xs)

    # 3. Create Internal Blocks
    # Two rectangular blocks in the center
    # Size adjusted to fit inside the 3.0um width
    block = gf.components.rectangle(size=(0.8, 0.6), layer=(1, 0), centered=True)
    
    # Position the blocks vertically
    b1 = c << block
    b1.movey(0.5)
    
    b2 = c << block
    b2.movey(-0.5)

    # 4. Create Connector Arms
    # Rectangles connecting the center blocks to the inner wall of the loop
    # Length of arm should cover the space between block (at center) and loop (at +/- 1.35 approx)
    arm = gf.components.rectangle(size=(0.7, 0.3), layer=(1, 0), centered=True)
    
    # Add 4 connectors (left/right of both top and bottom blocks)
    for y_pos in [0.5, -0.5]:
        for x_dir in [-1, 1]:
            arm_ref = c << arm
            arm_ref.move((x_dir * 0.75, y_pos))

    return c

# Generate and save
device = chain_link_device()
device.write_gds("racetrack_final.gds")