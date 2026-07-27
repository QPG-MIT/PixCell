import gdsfactory as gf

@gf.cell
def refined_device_silhouette():
    """
    Refined device geometry to match visual proportions of the original image.
    Total Footprint: 25um x 10um.
    """
    c = gf.Component("refined_device")
    layer = (1, 0)
    
    # --- 1. Main Rectangular Body ---
    # Centered at (0, 0), dimensions 25um x 4.2um
    body_w = 25.0
    body_h = 4.2
    rect = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    # Position the bottom edge of the rect at y=0.8 (leaving room for the tip)
    rect.movey(0.8 + body_h / 2) 
    
    # --- 2. Pillar Definition ---
    # Total pillar height is 5.0um (1.5um taper + 3.5um straight neck)
    pillar = gf.Component("pillar_unit")
    taper_h = 1.5
    neck_h = 3.5
    w_base = 1.8
    w_neck = 0.5
    
    # Tapered section
    p_taper = pillar << gf.components.taper(length=taper_h, width1=w_base, width2=w_neck, layer=layer)
    p_taper.rotate(90)
    
    # Straight neck section
    neck_xs = gf.cross_section.cross_section(width=w_neck, layer=layer)
    p_neck = pillar << gf.components.straight(length=neck_h, cross_section=neck_xs)
    p_neck.rotate(90)
    p_neck.connect("o1", p_taper.ports["o2"])
    
    # --- 3. Placement of 4 Pillars ---
    # Symmetrically spaced: outer pillars are closer to the edges
    pillar_x_positions = [-9.5, -3.5, 3.5, 9.5]
    for x in pillar_x_positions:
        p_ref = c << pillar
        # Place them on top of the main body (y = 0.8 + 4.2 = 5.0)
        p_ref.move((x, 5.0))
        
    # --- 4. Bottom Central Tip ---
    # A sharp taper pointing down from the center of the bottom edge
    tip_h = 0.8
    tip = c << gf.components.taper(length=tip_h, width1=1.2, width2=0.1, layer=layer)
    tip.rotate(-90)
    tip.movey(0.8) # Port o1 connects to the bottom of the rectangle
    
    return c

if __name__ == "__main__":
    device = refined_device_silhouette()
    device.write_gds("refined_device.gds")
    device.show()