import gdsfactory as gf

@gf.cell
def device_mmi_1x4():
    """
    Recreates the 1x4 MMI device from the image.
    Footprint constraint: 25um x 10um.
    """
    c = gf.Component()
    
    # --- Geometric Parameters ---
    # Total footprint is 25 x 10.
    # Vertical decomposition: Top Taper (3.0) + Body (5.0) + Bot Taper (2.0) = 10.0
    
    mmi_width = 25.0
    mmi_height = 5.0
    
    taper_len_top = 3.0
    taper_len_bot = 2.0
    
    # Widths estimated from image aspect ratios
    w_taper_tip = 1.0
    w_taper_base = 2.5
    
    # Pitch for the 4 top ports
    port_pitch = 5.0
    
    # --- 1. Main Body ---
    # Centered rectangle representing the MMI region
    # centered=True places the center at (0,0)
    body = c << gf.components.rectangle(
        size=(mmi_width, mmi_height), 
        layer=(1, 0), 
        centered=True
    )
    
    # --- 2. Top Ports (4 Tapers) ---
    # Define the taper primitive
    taper_top = gf.components.taper(
        length=taper_len_top, 
        width1=w_taper_tip, 
        width2=w_taper_base,
        layer=(1, 0)
    )
    
    # Calculate x positions centered around 0
    # For 4 ports: -7.5, -2.5, 2.5, 7.5
    x_positions = [-(1.5 * port_pitch) + (i * port_pitch) for i in range(4)]
    
    for x in x_positions:
        ref = c << taper_top
        # Rotate -90 degrees:
        # Standard taper: w1 (left) -> w2 (right)
        # Rotated -90: w1 (top) -> w2 (bottom)
        ref.rotate(-90)
        
        # FIX: Use ref.ports["o2"].center to get the actual (x,y) tuple of the port
        # "o2" is the wide base of the taper
        ref.move(origin=ref.ports["o2"].center, destination=(x, mmi_height / 2))
        
    # --- 3. Bottom Port (1 Taper) ---
    taper_bot = gf.components.taper(
        length=taper_len_bot, 
        width1=w_taper_tip, 
        width2=w_taper_base,
        layer=(1, 0)
    )
    
    ref_bot = c << taper_bot
    # Rotate 90 degrees: w1 (bottom) -> w2 (top)
    ref_bot.rotate(90)
    
    # FIX: Use ref.ports["o2"].center for the origin coordinate
    # Move wide base to the bottom edge of the body
    ref_bot.move(origin=ref_bot.ports["o2"].center, destination=(0, -mmi_height / 2))

    return c

if __name__ == "__main__":
    component = device_mmi_1x4()
    component.show()
    component.write_gds("mmi_1x4_recreation.gds")