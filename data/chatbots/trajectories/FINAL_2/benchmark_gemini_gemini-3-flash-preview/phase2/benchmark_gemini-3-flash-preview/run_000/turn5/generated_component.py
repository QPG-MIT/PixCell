import gdsfactory as gf

@gf.cell
def compound_pillar(taper_length=1.4, straight_length=3.1, w_base=2.4, w_mid=0.9, layer=(1, 0)):
    """
    Creates a pillar with a short tapered base and a longer, thinner neck.
    Total height = 4.5um
    """
    c = gf.Component()
    
    # Define cross-section for the straight neck
    xs = gf.cross_section.cross_section(width=w_mid, layer=layer)
    
    # Add the tapered base (shoulders)
    taper = c << gf.components.taper(
        length=taper_length, 
        width1=w_base, 
        width2=w_mid, 
        layer=layer
    )
    
    # Add the straight neck
    straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # Connect neck to taper and expose bottom port
    straight.connect("o1", taper.ports["o2"])
    c.add_port("o1", port=taper.ports["o1"])
    
    return c

@gf.cell
def recreated_device():
    """
    Final silhouette recreation with refined proportions for Turn 5.
    Total Footprint: ~22um (width) x 10um (height)
    """
    c = gf.Component("silhouette_v5")
    layer = (1, 0)
    
    # --- Vertical Budget (10.0um Total) ---
    # Bottom Taper: 1.0um
    # Body Height: 4.5um
    # Top Pillars: 4.5um
    body_w = 21.5
    body_h = 4.5
    
    # --- 1. Main Body ---
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # --- 2. Top Pillars (4 pillars) ---
    # Pitch of ~5.4um
    x_positions = [-8.1, -2.7, 2.7, 8.1]
    
    for x in x_positions:
        p = c << compound_pillar(
            taper_length=1.4, 
            straight_length=3.1, 
            w_base=2.2, 
            w_mid=0.8, 
            layer=layer
        )
        p.rotate(90)
        # Place base (o1) on the top edge of the body (y = 2.25)
        p.move(origin=p.ports["o1"].center, destination=(x, body_h/2))
        
    # --- 3. Bottom Pillar (Stubby wedge) ---
    bot_p = c << gf.components.taper(
        length=1.0, 
        width1=2.0, 
        width2=0.8, 
        layer=layer
    )
    bot_p.rotate(-90)
    # Place wide base on bottom edge of body (y = -2.25)
    bot_p.move(origin=bot_p.ports["o1"].center, destination=(0, -body_h/2))
    
    return c

if __name__ == "__main__":
    device = recreated_device()
    device.write_gds("silhouette_v5.gds")
    print(f"Device size: {device.xsize:.2f} x {device.ysize:.2f} um")
    
    try:
        device.show()
    except Exception:
        pass