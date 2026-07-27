import gdsfactory as gf

@gf.cell
def compound_pillar(taper_length=1.2, straight_length=2.8, w_base=2.0, w_mid=0.8, layer=(1, 0)):
    """
    Creates a pillar with a wide tapered base and a narrow straight neck.
    Total height = taper_length + straight_length (4.0um)
    """
    c = gf.Component()
    
    # 1. Define a cross-section for the straight part to avoid the TypeError
    xs = gf.cross_section.cross_section(width=w_mid, layer=layer)
    
    # 2. Add the tapered base
    # Note: If taper also throws a TypeError for 'layer', you can use a cross_section transition,
    # but usually taper accepts it directly for simple geometry.
    taper = c << gf.components.taper(length=taper_length, width1=w_base, width2=w_mid, layer=layer)
    
    # 3. Add the straight neck using the cross_section
    straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # 4. Connect and export port
    straight.connect("o1", taper.ports["o2"])
    c.add_port("o1", port=taper.ports["o1"])
    
    return c

@gf.cell
def recreated_device():
    """
    Final silhouette recreation with corrected component calls.
    Footprint constraint: 25um (width) x 10um (height)
    """
    c = gf.Component("final_silhouette_v3")
    layer = (1, 0)
    
    # --- Dimensions ---
    # Total Height (10.0um) = Bottom (1.0) + Body (5.0) + Top (4.0)
    body_w = 24.0
    body_h = 5.0
    top_p_h = 4.0
    bot_p_h = 1.0
    
    # --- 1. Main Body ---
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # --- 2. Top Pillars (4 Shoulder-style pillars) ---
    # Spacing pillars across the 24um body
    x_positions = [-9.0, -3.0, 3.0, 9.0]
    
    for x in x_positions:
        p = c << compound_pillar(
            taper_length=1.5, 
            straight_length=2.5, 
            w_base=2.0, 
            w_mid=0.8, 
            layer=layer
        )
        p.rotate(90)
        # Place base of pillar (o1) on the top edge of the body (y = 2.5)
        p.move(origin=p.ports["o1"].center, destination=(x, 2.5))
        
    # --- 3. Bottom Pillar (Single wide taper) ---
    bot_p = c << gf.components.taper(
        length=bot_p_h, 
        width1=2.6, 
        width2=1.2, 
        layer=layer
    )
    bot_p.rotate(-90)
    # Place base on bottom edge of body (y = -2.5)
    bot_p.move(origin=bot_p.ports["o1"].center, destination=(0, -2.5))
    
    return c

if __name__ == "__main__":
    # Generate component
    device = recreated_device()
    
    # Export and print stats
    filename = "corrected_device.gds"
    device.write_gds(filename)
    
    print(f"Successfully generated: {filename}")
    print(f"Total Width: {device.xsize:.2f} um (Target: 25.0)")
    print(f"Total Height: {device.ysize:.2f} um (Target: 10.0)")
    
    try:
        device.show()
    except Exception:
        pass