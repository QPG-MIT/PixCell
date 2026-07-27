import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Recreates the probe device with refined proportions for Turn 4.
    Target footprint: 25um (width) x 10um (height).
    """
    c = gf.Component("probe_device_v4")
    layer = (1, 0)

    # --- Vertical Dimension Budget (Total = 10.0um) ---
    body_h = 4.5          # Main rectangular body height
    top_taper_h = 1.2     # Tapered section of top fingers
    top_straight_h = 2.8  # Straight section of top fingers
    bottom_h = 1.5        # Short, stubby bottom feature
    # Total Height: 4.5 + 1.2 + 2.8 + 1.5 = 10.0um
    
    # --- Horizontal Dimension ---
    body_w = 16.0         # Wide rectangular body
    
    # 1. Main Body
    # Centered at (0,0)
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)

    # 2. Top Fingers (4 symmetric fingers)
    # Fingers are thinner at the tip than at the base
    w_base = 1.2
    w_tip = 0.8
    
    # Position fingers evenly. Spacing centers at 4um intervals.
    x_positions = [-6.0, -2.0, 2.0, 6.0]
    
    for x in x_positions:
        # Tapered base for the finger
        taper = gf.components.taper(length=top_taper_h, width1=w_base, width2=w_tip, layer=layer)
        t_ref = c << taper
        t_ref.rotate(90)
        t_ref.move((x, body_h / 2))
        
        # Straight vertical tip for the finger
        tip_xs = gf.cross_section.cross_section(width=w_tip, layer=layer)
        straight = gf.components.straight(length=top_straight_h, cross_section=tip_xs)
        s_ref = c << straight
        s_ref.rotate(90)
        s_ref.move((x, (body_h / 2) + top_taper_h))

    # 3. Bottom Feature (Centered stubby taper)
    # Matches the wide-based stub in the original image
    b_taper = gf.components.taper(length=bottom_h, width1=2.6, width2=0.6, layer=layer)
    b_ref = c << b_taper
    b_ref.rotate(-90)
    b_ref.move((0, -body_h / 2))

    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_device()
    
    # Export for viewing
    device.write_gds("probe_device_v4.gds")
    
    # Validation of constraints
    width = device.size_info.width
    height = device.size_info.height
    print(f"Validation:")
    print(f"  Device Width: {width:.2f} um (Target <= 25 um)")
    print(f"  Device Height: {height:.2f} um (Target <= 10 um)")