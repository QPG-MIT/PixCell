import gdsfactory as gf

@gf.cell
def custom_racetrack_device():
    # 1. Define Cross-section
    # We define a custom cross-section with a low radius_min 
    # to prevent the ValueError regarding tight bends.
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0), radius_min=0.1)

    # 2. Construct the Outer Loop using Path
    # Footprint analysis: 3.0um width -> Radius = 1.5um
    # Total height 5.5um -> Straight segments = 5.5 - (2 * 1.5) = 2.5um
    p = gf.Path()
    p.append(gf.path.arc(radius=1.5, angle=180))
    p.append(gf.path.straight(length=2.5))
    p.append(gf.path.arc(radius=1.5, angle=180))
    p.append(gf.path.straight(length=2.5))
    
    # Extrude path into the ring geometry
    loop = gf.path.extrude(p, cross_section=xs)

    # 3. Create Internal Components
    block = gf.components.rectangle(size=(0.8, 0.6), layer=(1, 0), centered=True)
    # Connector pieces to link blocks to the outer loop
    conn = gf.components.straight(length=0.4, cross_section=xs)

    # 4. Assembly
    # We create a temporary component to hold all pieces before merging
    temp_c = gf.Component()
    
    # Add Loop
    temp_c << loop
    
    # Add Blocks
    b1 = temp_c << block
    b2 = temp_c << block
    b1.movey(0.4)
    b2.movey(-0.4)
    
    # Add Connectors
    # We place 4 connectors to bridge the gap between blocks and the loop
    c1 = temp_c << conn
    c2 = temp_c << conn
    c3 = temp_c << conn
    c4 = temp_c << conn
    
    # Positioning connectors (relative to the center)
    c1.move((-0.4, 0.4))
    c2.move((0.4, 0.4))
    c3.move((-0.4, -0.4))
    c4.move((0.4, -0.4))

    # 5. Boolean Union
    # This takes all overlapping pieces in temp_c and merges them 
    # into a single, clean polygon structure.
    final_device = gf.boolean(A=temp_c, B=temp_c, operation="or", layer=(1, 0))
    
    return final_device

# Generate and save
device = custom_racetrack_device()
device.write_gds("racetrack_final.gds")