import gdsfactory as gf

@gf.cell
def racetrack_device():
    c = gf.Component()
    # Define standard layer
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=0.4, layer=layer)

    # 1. Build the Outer Racetrack Loop
    # Dimensions: Footprint 3.0 (width) x 5.5 (height)
    # Radius = 1.5 (diameter 3.0)
    # Straight length = 5.5 - (2 * 1.5) = 2.5
    
    p = gf.Path()
    # Start bottom-left of the right-side straight
    p.append(gf.path.straight(length=2.5))
    p.append(gf.path.arc(radius=1.5, angle=180))
    p.append(gf.path.straight(length=2.5))
    p.append(gf.path.arc(radius=1.5, angle=180))
    
    ring = gf.path.extrude(p, cross_section=xs)
    
    # 2. Build Internal Blocks and Connectors
    # The blocks are placed inside the ring
    block_size = (0.5, 1.2)
    conn_size = (0.4, 0.3)
    
    # Create internal features
    block_left = gf.components.rectangle(size=block_size, layer=layer)
    block_right = gf.components.rectangle(size=block_size, layer=layer)
    conn_left = gf.components.rectangle(size=conn_size, layer=layer)
    conn_right = gf.components.rectangle(size=conn_size, layer=layer)
    
    # 3. Assemble and Boolean Union
    # We add all parts to the component, then perform a boolean union
    # to merge the overlapping polygons into a single shape.
    
    # Place references
    r_ring = c << ring
    r_bl = c << block_left
    r_br = c << block_right
    r_cl = c << conn_left
    r_cr = c << conn_right
    
    # Position them
    # Ring is roughly centered at (1.5, 2.75) relative to its corner
    # Adjusting inner components to fit inside the 3.0 x 5.5 footprint
    r_bl.move((-0.3, 2.15))
    r_br.move((2.8, 2.15))
    r_cl.move((0.2, 2.6))
    r_cr.move((2.4, 2.6))
    
    # Perform Boolean OR to merge everything into one continuous shape
    # This prevents overlapping polygons and cleans up the geometry
    merged = gf.boolean(
        A=c, 
        B=c, 
        operation="or", 
        layer=layer
    )
    
    return merged

# Create the component
device = racetrack_device()

# Save the GDS file
device.write_gds("racetrack_device.gds")