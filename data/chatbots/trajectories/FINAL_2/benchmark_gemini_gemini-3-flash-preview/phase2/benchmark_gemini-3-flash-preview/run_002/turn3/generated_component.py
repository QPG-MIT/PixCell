import gdsfactory as gf

@gf.cell
def refined_device_v3():
    """
    Refined recreation of the device silhouette.
    Constraint: [25um width, 10um height]
    
    Proportions for target match:
    - Body: 20um wide, 4.5um high
    - Top Fingers (4x): 4.5um high total (2um taper + 2.5um straight tip)
    - Bottom Feature: 1.0um high trapezoid
    Total height = 4.5 + 4.5 + 1.0 = 10.0um
    """
    c = gf.Component("refined_device_turn3")
    layer = (1, 0)
    
    # 1. Body Dimensions
    body_w = 20.0
    body_h = 4.5
    
    # 2. Top Finger Design (Taper + Straight segment for flat tips)
    finger_taper_h = 2.0
    finger_straight_h = 2.5
    w_base = 3.0   # Base of the finger
    w_tip = 1.4    # Width of the top straight section
    
    # Create the finger parts
    taper_part = gf.components.taper(length=finger_taper_h, width1=w_base, width2=w_tip, layer=layer)
    straight_part = gf.components.straight(length=finger_straight_h, cross_section=gf.cross_section.cross_section(width=w_tip, layer=layer))
    
    # Combine them into a single finger component
    finger = gf.Component("single_finger")
    t_ref = finger << taper_part
    s_ref = finger << straight_part
    s_ref.connect("o1", t_ref.ports["o2"])
    
    # 3. Bottom Feature (Short, wide trapezoid)
    bot_h = 1.0
    bot_w1 = 4.0
    bot_w2 = 1.8
    bottom_feat = gf.components.taper(length=bot_h, width1=bot_w1, width2=bot_w2, layer=layer)

    # 4. Main Body
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 5. Assembly
    features = gf.Component("all_features")
    
    # Position 4 fingers
    # Evenly spaced across the 20um body
    x_positions = [-7.5, -2.5, 2.5, 7.5]
    for x in x_positions:
        f_ref = features << finger
        f_ref.rotate(90)
        # The base (o1 of taper_part) should sit on the body's top edge
        f_ref.move((x, body_h / 2))
        
    # Position bottom feature
    b_ref = features << bottom_feat
    b_ref.rotate(-90)
    b_ref.move((0, -body_h / 2))

    # 6. Final Boolean Merge
    # Merging ensures a clean single-polygon silhouette like the target
    merged = gf.boolean(A=body, B=features, operation="or", layer=layer)
    c << merged

    return c

if __name__ == "__main__":
    device = refined_device_v3()
    output_filename = "refined_device_v3.gds"
    device.write_gds(output_filename)
    print(f"Turn 3 GDS file generated: {output_filename}")