import gdsfactory as gf

@gf.cell
def recreate_device():
    # Initialize component and layer
    c = gf.Component("recreated_geometry")
    layer = (1, 0)

    # --- Dimensions based on 10um total height constraint ---
    # Top features height: 3.5um (2.5 taper + 1.0 straight)
    # Main body height: 5.0um
    # Bottom feature height: 1.5um
    # Total Height: 3.5 + 5.0 + 1.5 = 10.0um
    # Total Width: 20.0um (well within 25um limit)

    body_w = 20.0
    body_h = 5.0
    
    top_taper_h = 2.5
    top_straight_h = 1.0
    
    bottom_taper_h = 1.5

    # 1. Main Body
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)

    # 2. Top Fingers (4 symmetric fingers)
    # Define widths for the fingers
    w_base = 1.6
    w_tip = 0.8
    
    # Calculate horizontal spacing
    x_positions = [-7.5, -2.5, 2.5, 7.5]
    
    for x in x_positions:
        # Create Taper
        taper = gf.components.taper(length=top_taper_h, width1=w_base, width2=w_tip, layer=layer)
        t_ref = c << taper
        t_ref.rotate(90)
        # Position at top edge of body (y = 2.5)
        t_ref.move((x, body_h/2))
        
        # Create Straight tip
        tip_xs = gf.cross_section.cross_section(width=w_tip, layer=layer)
        straight = gf.components.straight(length=top_straight_h, cross_section=tip_xs)
        s_ref = c << straight
        s_ref.rotate(90)
        # Position at the end of the taper
        s_ref.move((x, (body_h/2) + top_taper_h))

    # 3. Bottom Feature (Centered Taper)
    b_taper = gf.components.taper(length=bottom_taper_h, width1=2.5, width2=1.2, layer=layer)
    b_ref = c << b_taper
    b_ref.rotate(-90)
    # Position at bottom edge of body (y = -2.5)
    b_ref.move((0, -body_h/2))

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreate_device()
    
    # Export to GDS file
    device.write_gds("device.gds")
    
    # Optional: Print info to console
    print("GDS file 'device.gds' has been generated.")
    print(f"Device size: {device.size_info.width:.2f} x {device.size_info.height:.2f} um")