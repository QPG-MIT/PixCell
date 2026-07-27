import gdsfactory as gf

@gf.cell
def mzm_in_racetrack() -> gf.Component:
    """
    Parametric creation of a Mach-Zehnder Modulator embedded within a racetrack resonator.
    Dimensions are explicitly designed to meet the 5.5 x 3.0 um footprint constraint 
    (oriented horizontally as shown in the reference image).
    """
    c = gf.Component()
    layer = (1, 0)
    
    # ---------------------------------------------------------
    # 1. Base Primitives & Parameters
    # ---------------------------------------------------------
    # Bounding box is 5.5 (width) x 3.0 (height)
    width = 5.5
    height = 3.0
    r_out = height / 2.0  # 1.5
    r_in = 1.0
    straight_len = width - 2 * r_out    # 5.5 - 3.0 = 2.5
    
    wg_width = 0.15
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)

    # ---------------------------------------------------------
    # 2. Outer Racetrack Ring Generation
    # ---------------------------------------------------------
    # Build outer pill
    rect_out = gf.components.rectangle(size=(straight_len, 2 * r_out), layer=layer, centered=True)
    circ_out = gf.components.circle(radius=r_out, layer=layer)
    
    c_out_l = gf.Component()
    c_out_l.add_ref(circ_out).move((-straight_len / 2, 0))
    
    c_out_r = gf.Component()
    c_out_r.add_ref(circ_out).move((straight_len / 2, 0))
    
    pill_out_step1 = gf.boolean(rect_out, c_out_l, operation='or', layer=layer)
    pill_out = gf.boolean(pill_out_step1, c_out_r, operation='or', layer=layer)

    # Build inner pill (hole)
    rect_in = gf.components.rectangle(size=(straight_len, 2 * r_in), layer=layer, centered=True)
    circ_in = gf.components.circle(radius=r_in, layer=layer)
    
    c_in_l = gf.Component()
    c_in_l.add_ref(circ_in).move((-straight_len / 2, 0))
    
    c_in_r = gf.Component()
    c_in_r.add_ref(circ_in).move((straight_len / 2, 0))
    
    pill_in_step1 = gf.boolean(rect_in, c_in_l, operation='or', layer=layer)
    pill_in = gf.boolean(pill_in_step1, c_in_r, operation='or', layer=layer)

    # Subtract to create ring
    ring = gf.boolean(pill_out, pill_in, operation='not', layer=layer)
    c << ring

    # ---------------------------------------------------------
    # 3. MZI Modulator Blocks
    # ---------------------------------------------------------
    # The modulators are solid blocks with two rectangular holes to form the phase shifting regions
    mod_len = 1.4
    mod_height = 0.5
    hole_width = 0.475  # Leaves 0.15m walls (0.15*3 + 0.475*2 = 1.4)
    hole_height = 0.2
    
    mod_block = gf.components.rectangle(size=(mod_len, mod_height), layer=layer, centered=True)
    hole = gf.components.rectangle(size=(hole_width, hole_height), layer=layer, centered=True)
    
    h1_comp = gf.Component()
    h1_comp.add_ref(hole).move((-0.3125, 0)) # -0.475/2 - 0.15/2
    
    h2_comp = gf.Component()
    h2_comp.add_ref(hole).move((0.3125, 0))  # 0.475/2 + 0.15/2
    
    mod_step1 = gf.boolean(mod_block, h1_comp, operation='not', layer=layer)
    mod_base = gf.boolean(mod_step1, h2_comp, operation='not', layer=layer)
    
    # Place top and bottom modulators
    y_arm = 0.45
    m1 = c << mod_base
    m1.move((0, y_arm))
    m2 = c << mod_base
    m2.move((0, -y_arm))

    # ---------------------------------------------------------
    # 4. MZI Splitters and Routing
    # ---------------------------------------------------------
    # Input/Output stems that connect the Y-branches to the inner racetrack wall
    # The inner wall of the racetrack straight segment is at x = -1.25, inner circle radius = 1.0 -> -2.25 max depth
    stem = gf.components.rectangle(size=(0.45, 0.4), layer=layer, centered=True)
    s1 = c << stem
    s1.move((-2.025, 0))
    s2 = c << stem
    s2.move((2.025, 0))

    # Small straight sections connecting modulators to diagonal Y-branches
    straight_conn = gf.components.rectangle(size=(0.3, wg_width), layer=layer, centered=True)
    conn_positions = [(-0.8, y_arm), (0.8, y_arm), (-0.8, -y_arm), (0.8, -y_arm)]
    for pos in conn_positions:
        sc = c << straight_conn
        sc.move(pos)

    # Diagonal Y-branch arms constructed via parametric path extrusion
    # The slight overlapping guarantees solid merging with no notches
    p_tl = gf.Path([(-1.85, 0), (-0.9, y_arm)])
    c << gf.path.extrude(p_tl, cross_section=xs)

    p_tr = gf.Path([(0.9, y_arm), (1.85, 0)])
    c << gf.path.extrude(p_tr, cross_section=xs)

    p_bl = gf.Path([(-1.85, 0), (-0.9, -y_arm)])
    c << gf.path.extrude(p_bl, cross_section=xs)

    p_br = gf.Path([(0.9, -y_arm), (1.85, 0)])
    c << gf.path.extrude(p_br, cross_section=xs)

    return c

if __name__ == "__main__":
    component = mzm_in_racetrack()
    # Write output to GDS to resolve the "No GDS file produced" error
    component.write_gds("mzm_in_racetrack.gds")