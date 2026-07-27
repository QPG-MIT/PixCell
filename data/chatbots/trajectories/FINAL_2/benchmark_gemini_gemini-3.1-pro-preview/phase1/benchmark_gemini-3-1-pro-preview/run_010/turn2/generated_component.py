import gdsfactory as gf

@gf.cell
def optical_splitter():
    c = gf.Component("optical_splitter")
    
    # We will strictly force everything onto layer (1,0)
    layer = (1, 0)
    
    # Footprint of the central MMI body
    body_width = 25.0
    body_height = 10.0
    
    # --- Adjusted Proportions ---
    # Top arms: shorter, steeper tapers followed by long straight pipes
    top_taper_len = 7.0       
    top_straight_len = 15.0   
    base_width = 2.8          
    tip_width = 1.0           
    
    # Bottom arm: single short taper
    bot_taper_len = 5.0       
    bot_base_width = 3.5      
    bot_tip_width = 1.2       
    
    # --- 1. Main Central Body ---
    body = c << gf.components.rectangle(
        size=(body_width, body_height), 
        layer=layer, 
        centered=True
    )
    
    # --- 2. Top Output Arms (4 Arms) ---
    pitch = body_width / 4.0
    x_centers = [-1.5 * pitch, -0.5 * pitch, 0.5 * pitch, 1.5 * pitch]
    
    for x in x_centers:
        # A. Taper Section
        taper = gf.components.taper(
            length=top_taper_len, 
            width1=base_width, 
            width2=tip_width, 
            layer=layer
        )
        t_ref = c << taper
        
        # Add a port to the top edge of the main body (orientation 90 = pointing UP)
        p_top = c.add_port(
            name=f"top_{x}", 
            center=(x, body_height / 2.0), 
            width=base_width, 
            orientation=90, 
            layer=layer
        )
        # Perfectly snap the taper's wide end to the body
        t_ref.connect("o1", p_top)
        
        # B. Straight Section
        # Trick: Using a taper with equal widths avoids CrossSection layer bugs 
        # and guarantees it renders identically to the taper geometries.
        straight = gf.components.taper(
            length=top_straight_len, 
            width1=tip_width, 
            width2=tip_width, 
            layer=layer
        )
        s_ref = c << straight
        # Snap straight section to the narrow end of the taper
        s_ref.connect("o1", t_ref.ports["o2"])

    # --- 3. Bottom Input Arm (1 Arm) ---
    bot_taper = gf.components.taper(
        length=bot_taper_len, 
        width1=bot_base_width, 
        width2=bot_tip_width, 
        layer=layer
    )
    b_ref = c << bot_taper
    
    # Add a port to the bottom edge of the main body (orientation -90 = pointing DOWN)
    p_bot = c.add_port(
        name="bot", 
        center=(0, -body_height / 2.0), 
        width=bot_base_width, 
        orientation=-90, 
        layer=layer
    )
    # Perfectly snap the bottom taper to the body
    b_ref.connect("o1", p_bot)

    return c

if __name__ == "__main__":
    device = optical_splitter()
    device.write_gds("optical_splitter.gds")
    print("Successfully generated 'optical_splitter.gds'")