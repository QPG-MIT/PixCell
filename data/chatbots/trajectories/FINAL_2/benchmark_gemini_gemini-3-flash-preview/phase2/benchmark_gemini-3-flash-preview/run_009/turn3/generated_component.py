import gdsfactory as gf

@gf.cell
def device_silhouette_v3():
    """
    Improved device geometry with chunky pillars and stubby bottom tip.
    Maintains the 25um x 10um footprint constraint.
    """
    c = gf.Component("device_v3")
    layer = (1, 0)
    
    # --- Dimensions ---
    total_w = 25.0
    total_h = 10.0
    
    tip_h = 1.0       # Bottom stub height
    body_h = 4.5      # Central body height
    pillar_h = 4.5    # Top pillars height (1.8um taper + 2.7um straight)
    
    # --- 1. Main Rectangular Body ---
    # Width: 25um. Positioned between y=1.0 and y=5.5
    body = c << gf.components.rectangle(size=(total_w, body_h), layer=layer, centered=True)
    body.movey(tip_h + body_h / 2)
    
    # --- 2. Top Pillar Definition ---
    pillar = gf.Component("pillar_unit")
    pillar_taper_h = 1.8
    pillar_straight_h = 2.7
    w_base = 3.2      # Base of the taper
    w_neck = 1.5      # Thick neck to match image
    
    # Tapered section
    p_taper = pillar << gf.components.taper(length=pillar_taper_h, width1=w_base, width2=w_neck, layer=layer)
    p_taper.rotate(90)
    
    # Straight neck section
    neck_xs = gf.cross_section.cross_section(width=w_neck, layer=layer)
    p_neck = pillar << gf.components.straight(length=pillar_straight_h, cross_section=neck_xs)
    p_neck.rotate(90)
    p_neck.connect("o1", p_taper.ports["o2"])
    
    # --- 3. Placement of 4 Pillars ---
    # Symmetrically spaced across the 25um width
    # Centers calculated to divide the space evenly: -9.375, -3.125, 3.125, 9.375
    pillar_x_positions = [-9.375, -3.125, 3.125, 9.375]
    for x in pillar_x_positions:
        p_ref = c << pillar
        # Move to top edge of the body (y = 5.5)
        p_ref.move((x, tip_h + body_h))
        
    # --- 4. Bottom Central Tip ---
    # A stubby, truncated taper pointing down
    tip_w1 = 2.2
    tip_w2 = 1.2
    tip = c << gf.components.taper(length=tip_h, width1=tip_w1, width2=tip_w2, layer=layer)
    tip.rotate(-90)
    # Port o1 (the base) is at the bottom of the body (y=1.0)
    tip.movey(tip_h)
    
    return c

if __name__ == "__main__":
    # Create the component
    component = device_silhouette_v3()
    
    # Output the GDS file
    component.write_gds("device_v3.gds")
    
    # Show the layout for verification
    component.show()