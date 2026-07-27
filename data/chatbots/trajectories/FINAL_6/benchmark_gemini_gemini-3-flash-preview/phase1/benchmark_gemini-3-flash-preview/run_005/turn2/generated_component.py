import gdsfactory as gf

@gf.cell
def recreate_cross_device_fixed():
    """
    Recreates the 4-lobed cross device geometry.
    Uses intersecting circles for tapered 'petal' lobes.
    Footprint constraint: 4.7um x 4.7um.
    """
    layer = (1, 0)
    
    # 1. Dimension calculations for 4.7um total span
    # Total half-span is 2.35um. 
    # We allocate 2.0um to the petal and 0.35um to the rectangular tip.
    half_span = 2.35
    tip_length = 0.35
    petal_len = 2.0
    petal_h_len = petal_len / 2
    petal_width = 1.0  # Width at the widest part of the petal
    petal_h_width = petal_width / 2

    # Math for Vesica Piscis (Intersection of two circles)
    # We need a radius R and an offset d such that the overlap has width W and length L
    d_offset = (petal_h_len**2 - petal_h_width**2) / (2 * petal_h_width)
    radius = d_offset + petal_h_width
    
    # Create the base circle component (Locked primitive)
    circ_base = gf.components.circle(radius=radius, layer=layer)
    
    # 2. Create the 'Petal' by intersecting two offset circles
    # We use container components to hold references and avoid the lock error
    c1_comp = gf.Component("top_circle_container")
    c1_comp.add_ref(circ_base).movey(d_offset) # Move the reference, not the cell
    
    c2_comp = gf.Component("bottom_circle_container")
    c2_comp.add_ref(circ_base).movey(-d_offset)
    
    # The intersection creates a pointed 'eye' shape centered at (0,0)
    petal_shape = gf.boolean(A=c1_comp, B=c2_comp, operation="and", layer=layer)

    # 3. Create the Arm template (One petal lobe + One tip)
    arm = gf.Component("arm_template")
    
    # Add petal: The eye shape is 2.0um long. We move it so its base is at (0,0).
    p_ref = arm << petal_shape
    p_ref.movex(petal_h_len) 
    
    # Add rectangular tip: 0.35um long, 0.18um wide
    tip_width = 0.18
    rect_tip = gf.components.rectangle(size=(tip_length, tip_width), layer=layer, centered=True)
    t_ref = arm << rect_tip
    t_ref.movex(petal_len + tip_length / 2)

    # 4. Assemble the final cross with 4-fold symmetry
    assembly = gf.Component("assembly_container")
    for angle in [0, 90, 180, 270]:
        arm_ref = assembly << arm
        arm_ref.rotate(angle)

    # 5. Final Boolean OR to merge the arms into a single solid silhouette
    # This ensures the center is a unified junction as seen in the target image
    device = gf.boolean(A=assembly, B=assembly, operation="or", layer=layer)
    
    return device

if __name__ == "__main__":
    # Generate the component
    final_comp = recreate_cross_device_fixed()
    
    # Output dimensions to verify footprint
    w = final_comp.dxsize
    h = final_comp.dysize
    print(f"Verified Footprint: {w:.3f} um x {h:.3f} um")
    
    # Export and show
    final_comp.write_gds("cross_device_final.gds")
    final_comp.show()