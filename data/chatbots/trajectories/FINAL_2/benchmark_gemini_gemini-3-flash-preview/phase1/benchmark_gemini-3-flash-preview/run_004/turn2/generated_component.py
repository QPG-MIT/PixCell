import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Recreates the probe device with corrected proportions to match the original image.
    Total height is exactly 10um to meet the footprint constraint.
    """
    c = gf.Component("probe_device")
    layer = (1, 0)

    # --- Dimensions ---
    # Total height = 10um. 
    # Proportions: Top Fingers (3.4um) + Body (5.0um) + Bottom Tip (1.6um) = 10um.
    # To match the original visual, we'll use a width of 10um.
    
    body_w = 10.0
    body_h = 5.0
    
    top_finger_total_h = 3.4
    top_taper_h = 1.4      # Short sharp taper base
    top_straight_h = 2.0   # Long thin needle tip
    
    bottom_h = 1.6
    
    # 1. Main Body
    # A central rectangular block
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)

    # 2. Top Fingers (4 symmetric thin fingers)
    # Narrower widths to match the "sharp" look of the original
    w_base = 0.9
    w_tip = 0.3
    
    # Position fingers closer to the edges, similar to the original image
    x_positions = [-4.0, -1.3, 1.3, 4.0]
    
    for x in x_positions:
        # Create Tapered base
        taper = gf.components.taper(length=top_taper_h, width1=w_base, width2=w_tip, layer=layer)
        t_ref = c << taper
        t_ref.rotate(90)
        t_ref.move((x, body_h / 2))
        
        # Create Thin straight tip
        tip_xs = gf.cross_section.cross_section(width=w_tip, layer=layer)
        straight = gf.components.straight(length=top_straight_h, cross_section=tip_xs)
        s_ref = c << straight
        s_ref.rotate(90)
        s_ref.move((x, (body_h / 2) + top_taper_h))

    # 3. Bottom Feature (Single needle-like taper)
    b_taper = gf.components.taper(length=bottom_h, width1=1.4, width2=0.2, layer=layer)
    b_ref = c << b_taper
    b_ref.rotate(-90)
    b_ref.move((0, -body_h / 2))

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreate_device()
    
    # Save the GDS file
    device.write_gds("probe_device.gds")
    
    # Print status and dimensions
    print("GDS file 'probe_device.gds' successfully created.")
    print(f"Device Width: {device.size_info.width:.2f} um (Constraint: 25 um)")
    print(f"Device Height: {device.size_info.height:.2f} um (Constraint: 10 um)")