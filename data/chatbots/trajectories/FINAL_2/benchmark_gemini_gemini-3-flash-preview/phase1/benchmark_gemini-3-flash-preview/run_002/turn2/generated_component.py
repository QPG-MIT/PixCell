import gdsfactory as gf

@gf.cell
def improved_device_recreation():
    """
    Recreates the device silhouette with improved proportions to match the target.
    Constraint: [25um width, 10um height]
    Proportions:
    - Top Tapers: 4.5um height (Longer, finger-like)
    - Body: 4.5um height
    - Bottom Taper: 1.0um height
    Total Height = 10.0um
    """
    c = gf.Component("device_final")
    layer = (1, 0)
    
    # 1. Define vertical proportions (totaling 10um)
    body_h = 4.5
    top_h = 4.5
    bot_h = 1.0
    body_w = 24.0 # Slightly less than 25 to leave breathing room or match footprint

    # 2. Create the rectangular body
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 3. Create the features
    # Top tapers: broader base (w1) and narrower tip (w2)
    top_taper = gf.components.taper(
        length=top_h, 
        width1=4.0,  # Increased base width for a more substantial look
        width2=1.2,  # Slender tip
        layer=layer
    )
    
    # Bottom taper: wide base, short length
    bot_taper = gf.components.taper(
        length=bot_h, 
        width1=5.0, 
        width2=1.5, 
        layer=layer
    )

    # 4. Assembly
    # We use a container to collect all features for a single boolean operation
    features = gf.Component("features_temp")
    
    # Distribute 4 top tapers
    # Centers at -9, -3, 3, 9 gives a pitch of 6um
    x_positions = [-9.0, -3.0, 3.0, 9.0]
    for x in x_positions:
        t_ref = features << top_taper
        t_ref.rotate(90)
        # Move base center to the top edge of the body
        t_ref.move((x, body_h / 2))
        
    # Add bottom taper at center
    b_ref = features << bot_taper
    b_ref.rotate(-90)
    # Move base center to the bottom edge of the body
    b_ref.move((0, -body_h / 2))

    # 5. Merge into a single silhouette using boolean 'or'
    # This ensures the final GDS contains one solid polygon as shown in your image
    merged = gf.boolean(A=body, B=features, operation="or", layer=layer)
    c << merged

    return c

if __name__ == "__main__":
    # Generate the device
    device = improved_device_recreation()
    
    # Define output filename and write to disk
    output_filename = "improved_device.gds"
    device.write_gds(output_filename)
    
    print(f"GDS file successfully generated: {output_filename}")