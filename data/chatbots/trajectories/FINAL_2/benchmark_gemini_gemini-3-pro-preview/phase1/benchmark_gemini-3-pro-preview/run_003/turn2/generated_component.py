import gdsfactory as gf

@gf.cell
def device_mmi_1x4_corrected():
    """
    Recreates the 1x4 MMI device with corrected geometry.
    Footprint constraint: 25um x 10um.
    Key geometric features: 
    - Top ports are composite (Straight + Flare).
    - Bottom port is a blunt taper.
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    # Total Footprint: 25um (Width) x 10um (Height)
    
    # Vertical Budget (Total = 10.0um):
    # 1. Top Prongs: 3.5um (2.5um straight + 1.0um flare)
    # 2. Main Body:  4.5um
    # 3. Bot Taper:  2.0um
    
    # Height Dimensions
    h_mmi = 4.5
    h_top_straight = 2.5
    h_top_flare = 1.0
    h_bot_taper = 2.0
    
    # Width Dimensions (Visual Estimation)
    w_mmi = 25.0
    w_top_straight = 1.5   # Thickness of the upper sticks
    w_top_base = 3.0       # Thickness at the connection to body
    w_bot_base = 3.0       # Thickness at bottom connection
    w_bot_tip = 0.8        # Tip thickness (not a sharp point)
    
    # Pitch for the 4 top ports
    # 4 ports distributed across 25um. 
    # Pitch ~6.0um gives positions [-9, -3, 3, 9], span 18um, margins 3.5um.
    port_pitch = 6.0
    
    # --- 1. Main Body ---
    body = c << gf.components.rectangle(
        size=(w_mmi, h_mmi), 
        layer=(1, 0), 
        centered=True
    )
    
    # --- 2. Top Ports (Composite: Straight + Flare) ---
    # We define a helper to build one prong
    def create_prong():
        p = gf.Component()
        
        # Part A: The Straight Section (Top)
        # Using taper with w1=w2 to create a straight segment
        s = p << gf.components.taper(
            length=h_top_straight,
            width1=w_top_straight,
            width2=w_top_straight,
            layer=(1, 0)
        )
        
        # Part B: The Flare Section (Bottom)
        # Taper expanding from straight width to base width
        t = p << gf.components.taper(
            length=h_top_flare,
            width1=w_top_straight,
            width2=w_top_base,
            layer=(1, 0)
        )
        
        # Connect: Small end of flare ('o1') to end of straight ('o2')
        t.connect("o1", s.ports["o2"])
        
        # Expose the wide base port ('o2' of the flare) as the anchor
        p.add_port("anchor", port=t.ports["o2"])
        return p

    # Instantiate the prong geometry once
    prong_template = create_prong()
    
    # Calculate x positions centered around 0
    x_positions = [-(1.5 * port_pitch) + (i * port_pitch) for i in range(4)]
    
    for x in x_positions:
        ref = c << prong_template
        # The prong is built Horizontal: Straight(Left) -> Flare(Right) -> Port(Right)
        # We need it Vertical: Straight(Top) -> Flare(Bottom) -> Port(Bottom)
        # Rotate -90 degrees
        ref.rotate(-90)
        
        # Move the anchor point to the top edge of the MMI body
        ref.move(origin=ref.ports["anchor"].center, destination=(x, h_mmi / 2))
        
    # --- 3. Bottom Port ---
    # Single taper, but blunted (finite tip width)
    taper_bot = gf.components.taper(
        length=h_bot_taper, 
        width1=w_bot_tip, 
        width2=w_bot_base,
        layer=(1, 0)
    )
    
    ref_bot = c << taper_bot
    # Orientation:
    # Standard taper: w1 (Tip) is at (0,0), w2 (Base) is at (length, 0)
    # We want Base at top (connected to body), Tip at bottom.
    # Rotate 90 deg: Base is at (0, length), Tip is at (0,0)
    ref_bot.rotate(90)
    
    # Move Base ('o2') to the bottom edge of the body
    ref_bot.move(origin=ref_bot.ports["o2"].center, destination=(0, -h_mmi / 2))

    return c

if __name__ == "__main__":
    component = device_mmi_1x4_corrected()
    component.show()
    component.write_gds("mmi_1x4_corrected.gds")