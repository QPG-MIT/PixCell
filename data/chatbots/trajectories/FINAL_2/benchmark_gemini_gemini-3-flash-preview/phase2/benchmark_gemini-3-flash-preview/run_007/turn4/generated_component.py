import gdsfactory as gf

@gf.cell
def create_device_silhouette_v4():
    """
    Refined device silhouette matching the target proportions.
    Total Footprint: 25um (Width) x 10um (Height).
    - Main Body: 25um x 6um
    - Top Pillars (4): 3um total height (1um taper + 2um straight)
    - Bottom Pillar (1): 1um total height (0.7um taper + 0.3um straight)
    """
    layer = (1, 0)
    
    # 1. Main Body
    # We use a 6um height to give the body more visual prominence.
    body_w = 25.0
    body_h = 6.0
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Top Pillar Template
    # Making the base wider and the taper shorter for a "sturdier" look.
    tp_taper_len = 1.0
    tp_straight_len = 2.0
    tp_w1 = 2.5  # Base width (noticeable wider)
    tp_w2 = 1.2  # Tip width
    
    tp_temp = gf.Component("tp_temp")
    t1 = tp_temp << gf.components.taper(length=tp_taper_len, width1=tp_w1, width2=tp_w2, layer=layer)
    s1 = tp_temp << gf.components.straight(length=tp_straight_len, 
                                           cross_section=gf.cross_section.cross_section(width=tp_w2, layer=layer))
    s1.connect("o1", t1.ports["o2"])
    
    # 3. Bottom Pillar Template
    # Shortened and slightly widened.
    bp_taper_len = 0.7
    bp_straight_len = 0.3
    bp_w1 = 2.2
    bp_w2 = 1.5
    
    bp_temp = gf.Component("bp_temp")
    t2 = bp_temp << gf.components.taper(length=bp_taper_len, width1=bp_w1, width2=bp_w2, layer=layer)
    s2 = bp_temp << gf.components.straight(length=bp_straight_len, 
                                           cross_section=gf.cross_section.cross_section(width=bp_w2, layer=layer))
    s2.connect("o1", t2.ports["o2"])
    
    # 4. Assembly
    # final_geo will hold the merged silhouette
    final_geo = body
    
    # Place 4 top pillars
    # Cluster positions slightly more towards center: [-7.5, -2.5, 2.5, 7.5]
    top_x_positions = [-7.5, -2.5, 2.5, 7.5]
    for x in top_x_positions:
        p_container = gf.Component()
        ref = p_container << tp_temp
        ref.rotate(90)
        # Move base to the top edge of the body (y = body_h/2)
        ref.move((x, body_h / 2))
        final_geo = gf.boolean(A=final_geo, B=p_container, operation="or", layer=layer)
        
    # Place 1 centered bottom pillar
    bot_container = gf.Component()
    b_ref = bot_container << bp_temp
    b_ref.rotate(-90)
    # Move base to the bottom edge of the body (y = -body_h/2)
    b_ref.move((0, -body_h / 2))
    final_geo = gf.boolean(A=final_geo, B=bot_container, operation="or", layer=layer)
    
    final_geo.name = "device_v4"
    return final_geo

if __name__ == "__main__":
    c = create_device_silhouette_v4()
    
    # The total Y span is from -4um (bottom pillar tip) to +6um (top pillar tips) = 10um height.
    # The total X span is 25um (body width).
    
    filename = "device_silhouette_v4.gds"
    c.write_gds(filename)
    print(f"Success! File saved as: {filename}")