import gdsfactory as gf

@gf.cell
def device_silhouette_v4():
    """
    Refined device geometry with broader pillars and adjusted body proportions.
    Maintains the 25um x 10um footprint constraint.
    """
    c = gf.Component("device_v4")
    layer = (1, 0)
    
    # --- Dimensions (Total height = 10.0um, Total width = 25.0um) ---
    total_w = 25.0
    
    tip_h = 1.2       # Bottom stub height
    body_h = 5.5      # Central body height (makes it look more substantial)
    pillar_h = 3.3    # Top pillars height (Total height budget: 1.2 + 5.5 + 3.3 = 10.0)
    
    # --- 1. Main Rectangular Body ---
    # Centered horizontally, positioned above the bottom tip.
    body = c << gf.components.rectangle(size=(total_w, body_h), layer=layer, centered=True)
    body.movey(tip_h + body_h / 2)
    
    # --- 2. Top Pillar Definition ---
    pillar = gf.Component("pillar_unit")
    pillar_taper_h = 2.2  # Taper is now the majority of the pillar
    pillar_straight_h = 1.1 
    w_base = 4.0          # Much wider base for the 'chunky' look
    w_neck = 2.4          # Thicker neck
    
    # Tapered section
    p_taper = pillar << gf.components.taper(length=pillar_taper_h, width1=w_base, width2=w_neck, layer=layer)
    p_taper.rotate(90)
    
    # Straight neck section
    neck_xs = gf.cross_section.cross_section(width=w_neck, layer=layer)
    p_neck = pillar << gf.components.straight(length=pillar_straight_h, cross_section=neck_xs)
    p_neck.rotate(90)
    p_neck.connect("o1", p_taper.ports["o2"])
    
    # --- 3. Placement of 4 Pillars ---
    # Symmetrically spaced across the 25um width.
    # Spacing centers: +/- 3.125 and +/- 9.375
    pillar_x_positions = [-9.375, -3.125, 3.125, 9.375]
    for x in pillar_x_positions:
        p_ref = c << pillar
        # Move to top edge of the body (y = 1.2 + 5.5 = 6.7)
        p_ref.move((x, tip_h + body_h))
        
    # --- 4. Bottom Central Tip ---
    # A wider, shorter stubby tip
    tip_w1 = 3.6  # Base width at the body interface
    tip_w2 = 2.2  # Width at the bottom tip
    tip = c << gf.components.taper(length=tip_h, width1=tip_w1, width2=tip_w2, layer=layer)
    tip.rotate(-90)
    # Move so the wider base (port o1) is at the bottom of the body (y=1.2)
    tip.movey(tip_h)
    
    return c

if __name__ == "__main__":
    # Create the component
    component = device_silhouette_v4()
    
    # Output the GDS file
    component.write_gds("device_v4.gds")
    
    # Show the layout for verification
    component.show()