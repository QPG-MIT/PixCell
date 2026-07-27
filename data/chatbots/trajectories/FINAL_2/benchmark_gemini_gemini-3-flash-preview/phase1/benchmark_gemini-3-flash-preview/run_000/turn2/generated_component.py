import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the device silhouette with refined slender proportions.
    Footprint constraint: 25um (width) x 10um (height)
    """
    c = gf.Component("refined_silhouette")
    layer = (1, 0)
    
    # --- 1. Main Body (Increased vertical prominence) ---
    # Width = 25um, Height = 6um. 
    # Centered at (0,0), Y-extent is -3.0 to 3.0
    body_w = 25.0
    body_h = 6.0
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # --- 2. Top Pillars (4 Slender Tapers) ---
    # Length = 3um. (Total Height: 1.0 Bottom + 6.0 Body + 3.0 Top = 10.0um)
    # Narrower widths to match the slender 'needle' look.
    top_len = 3.0
    top_w_base = 1.0  # Much thinner than previous versions
    top_w_tip = 0.5
    
    # Spacing adjusted to match the visual balance of the original image
    x_positions = [-8.5, -3.0, 3.0, 8.5]
    
    for x in x_positions:
        p = c << gf.components.taper(length=top_len, width1=top_w_base, width2=top_w_tip, layer=layer)
        p.rotate(90)
        # Snap base (o1) to top edge of body (y = 3.0)
        p.move(origin=p.ports["o1"].center, destination=(x, 3.0))
        
    # --- 3. Bottom Pillar (1 Taper) ---
    # Length = 1um.
    bot_len = 1.0
    bot_w_base = 1.8
    bot_w_tip = 0.8
    
    bot_p = c << gf.components.taper(length=bot_len, width1=bot_w_base, width2=bot_w_tip, layer=layer)
    bot_p.rotate(-90)
    # Snap base (o1) to bottom center of body (y = -3.0)
    bot_p.move(origin=bot_p.ports["o1"].center, destination=(0, -3.0))
    
    return c

if __name__ == "__main__":
    # Create the component
    device = recreated_device()
    
    # Explicitly save the GDS file
    filename = "refined_device.gds"
    device.write_gds(filename)
    
    # Print verification to console
    print(f"Successfully generated: {filename}")
    print(f"Width: {device.xsize} um")
    print(f"Height: {device.ysize} um")
    
    # Launch viewer if possible
    try:
        device.show()
    except Exception:
        pass