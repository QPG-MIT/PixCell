import gdsfactory as gf

@gf.cell
def device_reconstruction():
    """
    Recreates the device geometry using parametric primitives.
    Footprint constraint: 25um (width) x 10um (height).
    """
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # --- Dimensions (Optimized for 10um total height) ---
    # Total Height = Bottom Taper (2) + Body (4) + Top Taper (2) + Top Straight (2) = 10um
    body_w = 20.0
    body_h = 4.0
    
    prong_w_base = 1.8
    prong_w_tip = 0.8
    taper_l = 2.0
    straight_l = 2.0
    
    # 1. Define Cross Section for the straight segments
    # This prevents the 'layer' argument TypeError from the first attempt
    xs_prong = gf.cross_section.cross_section(width=prong_w_tip, layer=layer)
    
    # 2. Add Central Body
    # We use the rectangle primitive and center it at (0,0)
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 3. Add Top Prongs (4 units)
    # Positions are spaced symmetrically across the body
    x_offsets = [-7.5, -2.5, 2.5, 7.5]
    
    for x in x_offsets:
        # Create Taper segment
        taper = c << gf.components.taper(
            length=taper_l, 
            width1=prong_w_base, 
            width2=prong_w_tip, 
            layer=layer
        )
        taper.rotate(90)
        taper.move((x, body_h / 2)) # Align base to top edge of body
        
        # Create Straight segment
        straight = c << gf.components.straight(
            length=straight_l, 
            cross_section=xs_prong
        )
        straight.rotate(90)
        straight.move((x, (body_h / 2) + taper_l)) # Stack on top of taper
        
    # 4. Add Bottom Prong (1 unit)
    # Centered at the bottom
    bottom_prong = c << gf.components.taper(
        length=taper_l, 
        width1=prong_w_base, 
        width2=prong_w_tip, 
        layer=layer
    )
    bottom_prong.rotate(-90)
    bottom_prong.move((0, -body_h / 2)) # Align base to bottom edge of body
    
    return c

if __name__ == "__main__":
    device = device_reconstruction()
    
    # Fix: Using .xsize and .ysize which are compatible with modern GDSFactory/kfactory Component objects
    width = device.xsize
    height = device.ysize
    
    print(f"Calculated Dimensions: {width:.2f} um x {height:.2f} um")
    
    # Constraint verification logic
    if width <= 25.1 and height <= 10.1: # Allowing slight floating point margin
        print("Footprint Check: PASSED")
    else:
        print(f"Footprint Check: FAILED (Limit 25x10, Got {width}x{height})")
        
    device.show()