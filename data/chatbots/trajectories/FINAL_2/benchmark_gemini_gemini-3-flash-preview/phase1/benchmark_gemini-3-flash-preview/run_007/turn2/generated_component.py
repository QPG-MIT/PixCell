import gdsfactory as gf

@gf.cell
def create_refined_device():
    """
    Recreates the device silhouette based on the 25um (H) x 10um (W) footprint.
    Composition: Top Pillars (12um) + Body (8um) + Bottom Pillar (5um) = 25um Total Height.
    """
    layer = (1, 0)
    
    # 1. Main Body
    # A solid rectangle occupying the full width of the footprint
    body_w = 10.0
    body_h = 8.0
    body = gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Define the Top Pillar Sub-component
    # Length: 12um (8um taper + 4um straight tip)
    tp_taper_len = 8.0
    tp_straight_len = 4.0
    tp_w1 = 1.8  # Base width
    tp_w2 = 0.9  # Tip width
    
    tp_comp = gf.Component("top_pillar_template")
    t1 = tp_comp << gf.components.taper(length=tp_taper_len, width1=tp_w1, width2=tp_w2, layer=layer)
    s1 = tp_comp << gf.components.straight(length=tp_straight_len, 
                                           cross_section=gf.cross_section.cross_section(width=tp_w2, layer=layer))
    s1.connect("o1", t1.ports["o2"])
    
    # 3. Define the Bottom Pillar Sub-component
    # Length: 5um (3um taper + 2um straight tip)
    bp_taper_len = 3.0
    bp_straight_len = 2.0
    bp_w1 = 2.0  # Slightly wider base for the bottom pillar
    bp_w2 = 1.2
    
    bp_comp = gf.Component("bottom_pillar_template")
    t2 = bp_comp << gf.components.taper(length=bp_taper_len, width1=bp_w1, width2=bp_w2, layer=layer)
    s2 = bp_comp << gf.components.straight(length=bp_straight_len, 
                                           cross_section=gf.cross_section.cross_section(width=bp_w2, layer=layer))
    s2.connect("o1", t2.ports["o2"])
    
    # 4. Assembly using Boolean Union
    # Start with the body and merge each pillar into it
    final_geo = body
    
    # Place 4 top pillars with clustered spacing
    top_x_positions = [-3.6, -1.2, 1.2, 3.6]
    for x in top_x_positions:
        temp_container = gf.Component()
        ref = temp_container << tp_comp
        ref.rotate(90)
        ref.move((x, body_h / 2)) # Align base to top edge of body
        final_geo = gf.boolean(A=final_geo, B=temp_container, operation="or", layer=layer)
        
    # Place 1 centered bottom pillar
    bot_container = gf.Component()
    ref_b = bot_container << bp_comp
    ref_b.rotate(-90)
    ref_b.move((0, -body_h / 2)) # Align base to bottom edge of body
    final_geo = gf.boolean(A=final_geo, B=bot_container, operation="or", layer=layer)
    
    final_geo.name = "refined_device_silhouette"
    return final_geo

if __name__ == "__main__":
    # Create the component
    c = create_refined_device()
    
    # Generate the GDS file
    filename = "device_silhouette_refined.gds"
    c.write_gds(filename)
    
    print(f"File saved successfully: {filename}")