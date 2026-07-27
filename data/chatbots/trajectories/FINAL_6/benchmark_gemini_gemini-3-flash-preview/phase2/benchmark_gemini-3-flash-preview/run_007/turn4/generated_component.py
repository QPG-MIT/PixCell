import gdsfactory as gf

@gf.cell
def generate_recreated_device():
    """
    Refined recreation of the four-petal device.
    Features a very narrow central waist, slender almond-shaped petals,
    and prominent thin rectangular tips to match the target image.
    """
    c = gf.Component("recreated_device_v2")
    layer = (1, 0)
    
    # 1. Footprint Constraint
    # Total span is 4.7um x 4.7um
    total_length = 4.7
    half_len = total_length / 2.0
    
    # 2. Tip and Waist Parameters
    # Thinner width to create the 'pinched' look and delicate tips.
    tip_width = 0.18 
    cross_base = gf.components.cross(length=total_length, width=tip_width, layer=layer)
    
    # 3. Petal Parameters (The bulged sections)
    # rx: semi-major axis (length of the bulge)
    # ry: semi-minor axis (width of the bulge)
    # offset: distance from origin to the center of the ellipse
    petal_rx = 0.90  
    petal_ry = 0.42  
    # Setting offset slightly less than rx creates a tiny overlap at the center,
    # ensuring a connected but very thin waist.
    petal_offset = 0.89 
    
    # Math check:
    # Outer edge of petal: 0.89 + 0.90 = 1.79 um
    # Tip length: 2.35 - 1.79 = 0.56 um (Longer, distinct tips)
    # Center width: ~0.15 um at the junction.
    
    ellipse_base = gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    
    # 4. Assemble Petals
    petals = gf.Component("petals")
    
    # Right
    ref_r = petals << ellipse_base
    ref_r.movex(petal_offset)
    
    # Left
    ref_l = petals << ellipse_base
    ref_l.movex(-petal_offset)
    
    # Top
    ref_t = petals << ellipse_base
    ref_t.rotate(90)
    ref_t.movey(petal_offset)
    
    # Bottom
    ref_b = petals << ellipse_base
    ref_b.rotate(90)
    ref_b.movey(-petal_offset)
    
    # 5. Combine Geometry
    # OR-ing the cross with the petals creates the continuous structure 
    # where the cross forms the visible tips and the core 'skeleton'.
    final_geom = gf.boolean(A=petals, B=cross_base, operation="or", layer=layer)
    
    c << final_geom
    
    return c

if __name__ == "__main__":
    device = generate_recreated_device()
    device.write_gds("device.gds")
    # device.show()