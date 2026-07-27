import gdsfactory as gf

@gf.cell
def fork_device():
    """Creates the parametric fork/comb structure with a 25x10 footprint."""
    c = gf.Component("fork_device")
    
    layer = (1, 0)
    
    # --- Proportions & Constraints ---
    # Total footprint must be exactly 25 (width) x 10 (height)
    # The previous iteration had a body that was too short and tines that were too thick/close.
    # Adjusting proportions to increase body dominance and add more breathing room between tines.
    
    body_width = 25.0
    body_height = 5.0
    
    # Adjusted tine spacing and widths for better visual match
    tine_pitch = 4.8 
    tine_x_positions = [-7.2, -2.4, 2.4, 7.2] 
    
    # Heights must sum perfectly with body_height and nozzle_len to equal 10.0
    # 5.0 (body) + 2.4 (taper) + 1.4 (straight) + 1.2 (nozzle) = 10.0
    taper_len = 2.4
    tine_base_w = 3.0  
    tine_top_w = 1.2   
    straight_len = 1.4
    
    nozzle_len = 1.2
    nozzle_base_w = 2.0
    nozzle_tip_w = 0.6 

    # 1. Main Rectangular Body
    # Centered at Y=0, spans from Y=-2.5 to Y=2.5
    body = gf.components.rectangle(size=(body_width, body_height), layer=layer, centered=True)
    c << body

    # 2. Top Tines
    tine_taper = gf.components.taper(
        length=taper_len, 
        width1=tine_base_w, 
        width2=tine_top_w
    )
    
    tine_straight = gf.components.rectangle(
        size=(tine_top_w, straight_len), 
        layer=layer, 
        centered=True
    )
    
    for x in tine_x_positions:
        # Place the tapering base
        t_ref = c << tine_taper
        t_ref.rotate(90) # Standard taper faces X+, rotate to face Y+
        # Align wide base ('o1') to the top edge of the body
        t_ref.move((x, body_height / 2))
        
        # Place the straight rectangular top
        s_ref = c << tine_straight
        # Move rectangle so its bottom edge exactly touches the top of the taper
        s_ref.move((x, (body_height / 2) + taper_len + (straight_len / 2)))

    # 3. Bottom Nozzle
    nozzle = gf.components.taper(
        length=nozzle_len,
        width1=nozzle_base_w,
        width2=nozzle_tip_w
    )
    
    n_ref = c << nozzle
    n_ref.rotate(-90) # Rotate to face Y-
    # Align wide base ('o1') to the bottom edge of the body
    n_ref.move((0, -body_height / 2))

    return c

if __name__ == "__main__":
    # Create the device
    device = fork_device()
    
    # Save the geometry to a GDS file
    device.write_gds("fork_device.gds")