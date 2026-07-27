import gdsfactory as gf

@gf.cell
def custom_device():
    c = gf.Component()
    
    # 1. Define a custom cross-section with allowed small radius
    # This prevents the min_bend_radius ValueError
    xs = gf.cross_section.cross_section(
        width=0.4, 
        layer=(1, 0), 
        radius=1.0, 
        radius_min=0.1 
    )

    # 2. Build Outer Racetrack Loop using Path
    # Footprint constraint: 3.0 x 5.5
    # Radius 1.0 gives a loop width of 2.0 (fits in 3.0)
    # Straight length = 5.5 - 2*1.0 = 3.5
    p = gf.Path()
    p.append(gf.path.straight(length=3.5))
    p.append(gf.path.arc(radius=1.0, angle=180))
    p.append(gf.path.straight(length=3.5))
    p.append(gf.path.arc(radius=1.0, angle=180))
    
    # Extrude the path into the outer loop
    outer_loop = gf.path.extrude(p, cross_section=xs)
    
    # 3. Create Inner Rectangles and Connectors
    # Based on the image, we have two rectangles connected by small arms
    rect = gf.components.rectangle(size=(1.6, 0.8), layer=(1, 0), centered=True)
    arm = gf.components.straight(length=0.3, cross_section=xs)
    
    # Assembly
    # We add all parts to the component 'c'
    c << outer_loop
    
    # Top and bottom inner blocks
    for y_offset in [0.7, -0.7]:
        # Inner Rectangle
        block = c << rect
        block.movey(y_offset)
        
        # Connectors (Left and Right arms)
        for x_sign in [-1, 1]:
            b = c << arm
            b.movey(y_offset)
            # Position arm at edge of block
            b.movex(x_sign * (0.8 + 0.15)) 

    # 4. Final Boolean Union
    # The reference image is a solid, merged shape. 
    # We union all pieces to remove overlap lines.
    final_device = gf.boolean(c, c, operation="or", layer=(1, 0))
    
    # Return as a new Component
    device_final = gf.Component("final_racetrack_device")
    device_final.add_ref(final_device)
    
    return device_final

# Create and save
device = custom_device()
device.write_gds("final_device.gds")