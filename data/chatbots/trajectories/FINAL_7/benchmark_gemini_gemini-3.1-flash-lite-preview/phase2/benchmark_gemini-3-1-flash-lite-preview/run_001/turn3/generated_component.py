import gdsfactory as gf

@gf.cell
def custom_racetrack_device():
    # Define a component to hold the parts
    c = gf.Component()
    
    # 1. Define Cross-section
    # We define a standard cross-section
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))

    # 2. Construct the Outer Loop using Path
    # Footprint 3.0um width -> Radius = 1.5um
    # Total height 5.5um -> Straight segment = 5.5 - (2 * 1.5) = 2.5um
    p = gf.Path()
    p.append(gf.path.arc(radius=1.5, angle=180))
    p.append(gf.path.straight(length=2.5))
    p.append(gf.path.arc(radius=1.5, angle=180))
    p.append(gf.path.straight(length=2.5))
    
    # Extrude path into the ring geometry
    loop = c << gf.path.extrude(p, cross_section=xs)

    # 3. Create Internal Blocks
    # Two central blocks inside the loop
    block = gf.components.rectangle(size=(0.8, 0.6), layer=(1, 0), centered=True)
    b1 = c << block
    b2 = c << block
    b1.movey(0.5)
    b2.movey(-0.5)

    # 4. Create Connector Bridges
    # Small rectangles to bridge the gap between the internal blocks and the outer loop
    conn = gf.components.rectangle(size=(0.7, 0.3), layer=(1, 0), centered=True)
    
    # Add 4 connectors (one on each side of each block)
    for y_pos in [0.5, -0.5]:
        for x_sign in [-1, 1]:
            c_ref = c << conn
            # Positioning based on center (0,0)
            c_ref.move((x_sign * 0.75, y_pos))

    # 5. Boolean Union
    # This takes all overlapping pieces in component 'c' and merges them 
    # into a single, clean polygon structure.
    final_device = gf.boolean(A=c, B=c, operation="or", layer=(1, 0))
    
    return final_device

# Generate and save
device = custom_racetrack_device()
device.write_gds("racetrack_final.gds")