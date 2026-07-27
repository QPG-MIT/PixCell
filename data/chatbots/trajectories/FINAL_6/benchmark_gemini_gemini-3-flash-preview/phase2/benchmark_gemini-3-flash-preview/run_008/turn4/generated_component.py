import gdsfactory as gf

@gf.cell
def leaf_petal_arm():
    """
    Constructs one arm of the cross with a narrow base and a wide bulge.
    Total arm length: 2.35um (to meet the 4.7um footprint constraint).
    """
    c = gf.Component()
    layer = (1, 0)
    
    # --- GEOMETRY PARAMETERS ---
    # Lengths (Total = 2.35um)
    l_expand = 1.10    # Distance from center to widest point
    l_taper = 0.90     # Distance from widest point back to narrow neck
    l_tip = 0.35       # Length of the final rectangular tip
    
    # Widths
    w_start = 0.15     # Narrow at center to ensure distinct petals
    w_bulge = 1.95     # Wide bulge (nearly touches adjacent arms at 45 degrees)
    w_neck = 0.35      # Narrow neck before the tip
    
    # --- CROSS SECTIONS ---
    xs_start = gf.cross_section.cross_section(width=w_start, layer=layer)
    xs_bulge = gf.cross_section.cross_section(width=w_bulge, layer=layer)
    xs_neck = gf.cross_section.cross_section(width=w_neck, layer=layer)
    
    # --- CONSTRUCTION ---
    # 1. Expansion segment: Center -> Maximum bulge
    p1 = gf.path.straight(length=l_expand)
    t1 = gf.path.transition(xs_start, xs_bulge, width_type='sine')
    s1 = c << gf.path.extrude_transition(p1, t1)
    
    # 2. Contraction segment: Bulge -> Neck
    p2 = gf.path.straight(length=l_taper)
    t2 = gf.path.transition(xs_bulge, xs_neck, width_type='sine')
    s2 = c << gf.path.extrude_transition(p2, t2)
    s2.connect("o1", s1.ports["o2"])
    
    # 3. Rectangular Tip segment
    s3 = c << gf.components.straight(length=l_tip, cross_section=xs_neck)
    s3.connect("o1", s2.ports["o2"])
    
    # Set the origin port for rotation at the center of the cross
    c.add_port("o1", port=s1.ports["o1"])
    return c

@gf.cell
def bulging_cross_recreation():
    """
    Assembles four leaf-like petals into the final cross.
    Total Footprint: 4.7um x 4.7um.
    """
    c = gf.Component()
    arm = leaf_petal_arm()
    
    # Add and rotate four arm instances
    for i in range(4):
        ref = c << arm
        ref.rotate(90 * i)
        
    # The arms now meet at a narrow point, preserving the 'pinched' center
    return c

if __name__ == "__main__":
    # Create the component
    component = bulging_cross_recreation()
    
    # Final check of footprint dimensions
    print(f"Final Footprint: {component.dxsize:.2f} um x {component.dysize:.2f} um")
    
    # Visualization and export
    component.show()
    component.write_gds("bulging_cross_v4.gds")