import gdsfactory as gf

@gf.cell
def generate_recreated_device():
    """
    Recreates the device with a highly pinched center and prominent rectangular tips.
    Uses four offset ellipses for the 'petals' and a central cross to define the
    waist and the four rectangular extremities.
    """
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # 1. Total Footprint constraint: 4.7um x 4.7um
    total_length = 4.7
    half_len = total_length / 2.0
    
    # 2. Cross Parameters (Waist and Tips)
    # This width defines both the central 'pinch' and the tip thickness.
    tip_width = 0.3 
    cross_base = gf.components.cross(length=total_length, width=tip_width, layer=layer)
    
    # 3. Petal Parameters (Leaf shape)
    # rx: Semi-major axis (length of the petal)
    # ry: Semi-minor axis (width of the petal)
    # offset: Distance from center to the ellipse center
    petal_rx = 0.85  
    petal_ry = 0.55  
    petal_offset = 1.15 
    
    # Calculate key points for visualization:
    # Inner edge of petal: offset - rx = 1.15 - 0.85 = 0.3um (creates the pinched waist)
    # Outer edge of petal: offset + rx = 1.15 + 0.85 = 2.0um
    # Tip length: half_len - outer_edge = 2.35 - 2.0 = 0.35um
    
    # Create the base ellipse primitive
    ellipse_base = gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    
    # 4. Assemble Petals
    petals = gf.Component("petals")
    
    # Right Petal
    ref_r = petals << ellipse_base
    ref_r.movex(petal_offset)
    
    # Left Petal
    ref_l = petals << ellipse_base
    ref_l.movex(-petal_offset)
    
    # Top Petal (Rotated 90 degrees)
    ref_t = petals << ellipse_base
    ref_t.rotate(90)
    ref_t.movey(petal_offset)
    
    # Bottom Petal (Rotated 90 degrees)
    ref_b = petals << ellipse_base
    ref_b.rotate(90)
    ref_b.movey(-petal_offset)
    
    # 5. Merge Geometry
    # The boolean OR merges the thin cross with the petals.
    # Because the petals are offset outward, the cross remains visible at the 
    # center (creating the waist) and at the ends (creating the tips).
    final_geom = gf.boolean(A=petals, B=cross_base, operation="or", layer=layer)
    
    # Add to main component
    c << final_geom
    
    return c

if __name__ == "__main__":
    device = generate_recreated_device()
    device.write_gds("device.gds")
    # For visualization in notebook environments:
    # device.show()