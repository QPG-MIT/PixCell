import gdsfactory as gf

@gf.cell
def fork_device():
    """Creates the parametric fork/comb structure with a 25x10 footprint."""
    c = gf.Component("fork_device")
    
    layer = (1, 0)
    
    # --- Proportions & Constraints ---
    # Total footprint must be 25 (width) x 10 (height)
    # Total Height (10) = Top Straight (2.0) + Top Taper (2.5) + Body (4.0) + Bottom Nozzle (1.5)
    
    body_width = 25.0
    body_height = 4.0
    
    tine_pitch = 5.0
    # Center points for the 4 tines
    tine_x_positions = [-7.5, -2.5, 2.5, 7.5] 
    
    taper_len = 2.5
    tine_base_w = 3.5  # Wider base to match the original
    tine_top_w = 1.5   # Thicker straight part to match the original
    straight_len = 2.0
    
    nozzle_len = 1.5
    nozzle_base_w = 2.5
    nozzle_tip_w = 1.0 # Blunter flat tip to match the original

    # 1. Main Rectangular Body
    # Centered at Y=0, spans from Y=-2.0 to Y=2.0
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
        # Align wide base ('o1') to the top edge of the body (Y = 2.0)
        t_ref.move((x, body_height / 2))
        
        # Place the straight rectangular top
        s_ref = c << tine_straight
        # Move rectangle so its bottom edge touches the top of the taper
        # Center Y = body top (2.0) + taper_len (2.5) + half straight_len (1.0) = 5.5
        s_ref.move((x, (body_height / 2) + taper_len + (straight_len / 2)))

    # 3. Bottom Nozzle
    nozzle = gf.components.taper(
        length=nozzle_len,
        width1=nozzle_base_w,
        width2=nozzle_tip_w
    )
    
    n_ref = c << nozzle
    n_ref.rotate(-90) # Rotate to face Y-
    # Align wide base ('o1') to the bottom edge of the body (Y = -2.0)
    n_ref.move((0, -body_height / 2))

    return c

if __name__ == "__main__":
    # Create the device
    device = fork_device()
    
    # Save the geometry to a GDS file
    device.write_gds("fork_device.gds")