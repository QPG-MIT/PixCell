import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Recreates the probe device for Turn 5.
    Focus: Increasing width of body and fingers, and blunting the bottom tip.
    Target footprint: 25um (width) x 10um (height).
    """
    c = gf.Component("probe_device_v5")
    layer = (1, 0)

    # --- Vertical Dimension Budget (Total = 10.0um) ---
    # We allocate more height to the body to match the original image's weight.
    body_h = 5.0          
    top_taper_h = 1.0     
    top_straight_h = 2.5  
    bottom_h = 1.5        
    # Total Height: 5.0 + 1.0 + 2.5 + 1.5 = 10.0um
    
    # --- Horizontal Dimension ---
    # Wider body to match the original aspect ratio
    body_w = 22.0         
    
    # 1. Main Body
    # Centered at (0,0)
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)

    # 2. Top Fingers (4 symmetric fingers)
    # Increased widths for a "chunkier" look
    w_base = 2.2
    w_tip = 1.6
    
    # Positions spaced evenly across the wider 22um body
    # Center-to-center spacing of roughly 5.5um
    x_positions = [-8.5, -3.0, 3.0, 8.5]
    
    for x in x_positions:
        # Tapered base (shorter and wider)
        taper = gf.components.taper(length=top_taper_h, width1=w_base, width2=w_tip, layer=layer)
        t_ref = c << taper
        t_ref.rotate(90)
        t_ref.move((x, body_h / 2))
        
        # Rectangular tip (thicker)
        tip_xs = gf.cross_section.cross_section(width=w_tip, layer=layer)
        straight = gf.components.straight(length=top_straight_h, cross_section=tip_xs)
        s_ref = c << straight
        s_ref.rotate(90)
        s_ref.move((x, (body_h / 2) + top_taper_h))

    # 3. Bottom Feature (Truncated taper)
    # Matches the wide-based blunt stub in the original image
    # width2 is increased to avoid a sharp point
    b_taper = gf.components.taper(length=bottom_h, width1=3.5, width2=1.5, layer=layer)
    b_ref = c << b_taper
    b_ref.rotate(-90)
    b_ref.move((0, -body_h / 2))

    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_device()
    
    # Export for viewing
    device.write_gds("probe_device_v5.gds")
    
    # Validation of constraints
    width = device.size_info.width
    height = device.size_info.height
    print(f"Validation:")
    print(f"  Device Width: {width:.2f} um (Target <= 25 um)")
    print(f"  Device Height: {height:.2f} um (Target <= 10 um)")