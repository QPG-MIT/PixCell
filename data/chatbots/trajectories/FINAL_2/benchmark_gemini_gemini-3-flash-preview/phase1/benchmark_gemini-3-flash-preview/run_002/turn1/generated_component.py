import gdsfactory as gf

@gf.cell
def create_device_geometry():
    """
    Recreates the device silhouette from the image using parametric primitives.
    Total Footprint: 25um (width) x 10um (height)
    """
    c = gf.Component("device_recreation")
    layer = (1, 0)
    
    # 1. Dimensions derived from the 25x10um footprint
    # We split the 10um height into: top features (2.5) + body (6.0) + bottom (1.5)
    body_w = 25.0
    body_h = 6.0
    top_feature_h = 2.5
    bot_feature_h = 1.5

    # 2. Create the central body
    # centered=True puts the center of the 25x6 rectangle at (0,0)
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    c << body
    
    # 3. Add 4 Top Tapers
    # A taper primitive starts with port 'o1' at (0,0) and extends to 'o2' at (length, 0)
    top_taper = gf.components.taper(
        length=top_feature_h, 
        width1=2.6, # Base width
        width2=1.2, # Tip width
        layer=layer
    )
    
    # Positions to distribute 4 tapers across the 25um width
    x_positions = [-9.0, -3.0, 3.0, 9.0]
    for x in x_positions:
        t_ref = c << top_taper
        # Rotate 90 degrees: o1 stays at (0,0), o2 (tip) moves to (0, 2.5)
        t_ref.rotate(90)
        # Move the base (at 0,0) to the top edge of the body (y = 3.0)
        t_ref.move((x, body_h / 2))
        
    # 4. Add 1 Bottom Taper
    bot_taper = gf.components.taper(
        length=bot_feature_h, 
        width1=4.0, # Wider base for the single bottom feature
        width2=2.0, # Tip width
        layer=layer
    )
    b_ref = c << bot_taper
    # Rotate -90 degrees: o1 stays at (0,0), o2 (tip) moves to (0, -1.5)
    b_ref.rotate(-90)
    # Move the base (at 0,0) to the bottom edge of the body (y = -3.0)
    b_ref.move((0, -body_h / 2))

    return c

if __name__ == "__main__":
    # Generate the component
    device = create_device_geometry()
    
    # Save to GDS file
    output_path = "device_recreation.gds"
    device.write_gds(output_path)
    
    print(f"Success! GDS file produced: {output_path}")