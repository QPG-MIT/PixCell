import gdsfactory as gf

@gf.cell
def refined_device_v5():
    """
    Refined recreation of the device silhouette (Turn 5).
    Constraint: [25um width, 10um height]
    
    Adjustments for Turn 5:
    - Widened body to 22um for better aspect ratio match.
    - Adjusted fingers: Slenderer base, longer straight tips (1.8um).
    - Spacing: Centers at +/- 8.25 and +/- 2.75 to provide realistic edge margins.
    - Bottom Feature: Flattened to a blunt trapezoid (0.8um high, 2.0um tip).
    Total height breakdown: 3.8 (top) + 5.4 (body) + 0.8 (bottom) = 10.0um.
    """
    c = gf.Component("refined_device_turn5")
    layer = (1, 0)
    
    # 1. Height Budget (Total = 10.0um)
    body_h = 5.4
    finger_total_h = 3.8
    bottom_h = 0.8
    
    # 2. Width Budget
    body_w = 22.0 
    
    # 3. Top Finger Design
    # Balanced taper and straight segments for a more "pill" like look at the tip
    finger_taper_h = 2.0
    finger_straight_h = 1.8
    w_base = 2.2
    w_tip = 1.1
    
    # Finger components
    taper_part = gf.components.taper(length=finger_taper_h, width1=w_base, width2=w_tip, layer=layer)
    straight_part = gf.components.straight(length=finger_straight_h, cross_section=gf.cross_section.cross_section(width=w_tip, layer=layer))
    
    finger = gf.Component("single_finger")
    t_ref = finger << taper_part
    s_ref = finger << straight_part
    s_ref.connect("o1", t_ref.ports["o2"])
    
    # 4. Bottom Feature Design (Blunt trapezoid)
    bot_w_base = 3.2
    bot_w_tip = 2.0
    bottom_feat = gf.components.taper(length=bottom_h, width1=bot_w_base, width2=bot_w_tip, layer=layer)

    # 5. Main Body
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 6. Assembly
    features = gf.Component("all_features")
    
    # Position 4 fingers with center-to-center spacing of 5.5um
    # This leaves a ~1.65um shelf on the edges of the 22um body
    x_positions = [-8.25, -2.75, 2.75, 8.25]
    
    for x in x_positions:
        f_ref = features << finger
        f_ref.rotate(90)
        # Align finger base (o1) to the top edge of the body
        f_ref.move((x, body_h / 2))
        
    # Position bottom feature centrally
    b_ref = features << bottom_feat
    b_ref.rotate(-90)
    b_ref.move((0, -body_h / 2))

    # 7. Final Merge using Boolean OR
    merged = gf.boolean(A=body, B=features, operation="or", layer=layer)
    c << merged

    return c

if __name__ == "__main__":
    # Generate and save the GDS
    device = refined_device_v5()
    output_filename = "refined_device_v5.gds"
    device.write_gds(output_filename)
    print(f"Turn 5 GDS file generated: {output_filename}")