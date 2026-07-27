import gdsfactory as gf

@gf.cell
def recreate_cross_device_v5():
    """
    Refines the cross-shaped device to match the target image's organic leaf profile.
    
    Changes:
    - Reduced w_center to create sharp 'pinches' between petals.
    - Adjusted taper lengths for a more balanced leaf shape.
    - Footprint constraint: 4.7um x 4.7um (Radius = 2.35um).
    """
    c = gf.Component("organic_leaf_cross")
    
    # 1. Dimensions for exactly 4.7um footprint (Radius = 2.35um)
    # Total = 1.0 (expand) + 0.95 (taper) + 0.4 (tip) = 2.35um
    p1_len = 1.0    # Length from center to the widest part of the leaf
    p2_len = 0.95   # Length from widest part to the start of the tip
    tip_len = 0.4   # Length of the narrow rectangular end tip
    
    # Widths to match visual proportions
    w_center = 0.05  # Very narrow start to create distinct petals
    w_max = 1.5      # Maximum bulge width of the petal leaf
    w_tip = 0.3      # Width of the outer rectangular tip
    
    # 2. Define Cross-Sections
    xs_center = gf.cross_section.cross_section(width=w_center, layer=(1, 0))
    xs_max = gf.cross_section.cross_section(width=w_max, layer=(1, 0))
    xs_tip = gf.cross_section.cross_section(width=w_tip, layer=(1, 0))
    
    # 3. Create a single Petal/Arm Component
    arm = gf.Component("petal_arm")
    
    # Part A: Center to Max Width (Organic expansion)
    trans1 = gf.path.transition(cross_section1=xs_center, cross_section2=xs_max, width_type="sine")
    p1 = arm << gf.path.extrude_transition(gf.path.straight(length=p1_len), transition=trans1)
    
    # Part B: Max Width to Tip Width (Organic taper)
    trans2 = gf.path.transition(cross_section1=xs_max, cross_section2=xs_tip, width_type="sine")
    p2 = arm << gf.path.extrude_transition(gf.path.straight(length=p2_len), transition=trans2)
    p2.movex(p1_len)
    
    # Part C: The Rectangular End Tip
    tip = arm << gf.components.straight(length=tip_len, cross_section=xs_tip)
    tip.movex(p1_len + p2_len)
    
    # 4. Assemble the full cross using rotational symmetry
    for angle in [0, 90, 180, 270]:
        arm_ref = c << arm
        arm_ref.rotate(angle)
    
    # 5. Clean up geometry with Boolean OR
    # This merges the 4 arms into a single continuous polygon.
    return gf.boolean(A=c, B=c, operation="or", layer=(1, 0))

if __name__ == "__main__":
    # Generate the device
    device = recreate_cross_device_v5()
    
    # Write GDS file
    device.write_gds("cross_device_v5.gds")
    
    # Verification Output
    # Expected: ~4.70 um
    print(f"Device width: {device.dxsize:.3f} um")
    print(f"Device height: {device.dysize:.3f} um")
    
    # Display the result
    device.show()