import gdsfactory as gf

@gf.cell
def leaf_petal_arm():
    """
    Constructs one arm of the cross with a smooth, leaf-like bulging profile.
    Total arm length is 2.35um, ensuring a 4.7um total device span.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define segment lengths (total must be 2.35um)
    l_expand = 1.05    # Length from center to widest point
    l_taper = 1.00     # Length from widest point to the 'neck'
    l_tip = 0.30       # Length of the straight rectangular tip
    
    # 2. Define widths for the profile
    w_core = 0.9       # Width at the center junction (ensures a solid merge)
    w_bulge = 2.3      # Max width of the petal (increased for "plump" look)
    w_tip = 0.35       # Width of the rectangular terminal
    
    # 3. Create Cross-Sections for transitions
    xs_core = gf.cross_section.cross_section(width=w_core, layer=layer)
    xs_bulge = gf.cross_section.cross_section(width=w_bulge, layer=layer)
    xs_tip = gf.cross_section.cross_section(width=w_tip, layer=layer)
    
    # 4. Build the petal using Path Extrusion
    # Segment A: Expansion (Center -> Bulge)
    p1 = gf.path.straight(length=l_expand)
    t1 = gf.path.transition(xs_core, xs_bulge, width_type='sine')
    s1 = c << gf.path.extrude_transition(p1, t1)
    
    # Segment B: Contraction (Bulge -> Neck)
    p2 = gf.path.straight(length=l_taper)
    t2 = gf.path.transition(xs_bulge, xs_tip, width_type='sine')
    s2 = c << gf.path.extrude_transition(p2, t2)
    s2.connect("o1", s1.ports["o2"])
    
    # Segment C: Rectangular Tip
    s3 = c << gf.components.straight(length=l_tip, cross_section=xs_tip)
    s3.connect("o1", s2.ports["o2"])
    
    # Add port at origin for easy rotation
    c.add_port("o1", port=s1.ports["o1"])
    return c

@gf.cell
def bulging_cross_recreation():
    """
    Assembles four leaf-like petals into a cross with a 4.7um footprint.
    """
    c = gf.Component()
    arm = leaf_petal_arm()
    
    for i in range(4):
        ref = c << arm
        ref.rotate(90 * i)
        
    # Ensure the central junction is perfectly filled with a small circle
    # This smooths the transitions where the four arms meet
    c << gf.components.circle(radius=0.45, layer=(1, 0))
    
    return c

if __name__ == "__main__":
    component = bulging_cross_recreation()
    
    # Verification of 4.7um footprint
    print(f"Device width: {component.dxsize:.3f} um")
    print(f"Device height: {component.dysize:.3f} um")
    
    component.show()
    component.write_gds("refined_bulging_cross.gds")