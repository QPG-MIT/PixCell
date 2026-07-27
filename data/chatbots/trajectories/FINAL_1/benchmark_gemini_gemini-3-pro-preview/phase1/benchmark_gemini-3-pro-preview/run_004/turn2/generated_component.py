import gdsfactory as gf

@gf.cell
def inverse_taper_ssc():
    """
    Inverse taper spot size converter.
    Features a central taper ending in a tip, surrounded by cladding arms 
    that expand to form the output waveguide.
    """
    c = gf.Component()

    # --- Dimensions ---
    L_total = 40.0
    height = 1.7
    layer = (1, 0)

    # Longitudinal parameters
    L_taper = 20.0      # Central taper length
    L_trans = 30.0      # Length where arms expand
    L_flat = L_total - L_trans # Remaining length for merged block

    # Width parameters
    w_taper_in = 0.7
    w_taper_tip = 0.05
    w_arm_start = 0.4
    w_arm_end = 0.85    # height / 2.0

    # --- 1. Central Taper ---
    taper = c << gf.components.taper(
        length=L_taper,
        width1=w_taper_in,
        width2=w_taper_tip,
        layer=layer
    )
    taper.move((0, 0))

    # --- 2. Top Arm Construction ---
    # We construct the arm in two parts: 
    # Part A: Transition (Widening with straight outer edge)
    # Part B: Straight (Merged output)

    # Path for transition lies on the top boundary (y = +height/2)
    path_top_a = gf.path.straight(length=L_trans)
    
    # Define sections relative to the path (offset = -width/2 keeps top edge on path)
    s_top_in = gf.Section(
        width=w_arm_start, 
        offset=-w_arm_start/2, 
        layer=layer, 
        name="arm"
    )
    s_top_out = gf.Section(
        width=w_arm_end, 
        offset=-w_arm_end/2, 
        layer=layer, 
        name="arm"
    )
    
    xs_top_in = gf.CrossSection(sections=[s_top_in])
    xs_top_out = gf.CrossSection(sections=[s_top_out])
    
    # 'sine' width type gives the characteristic S-bend inner profile
    trans_top = gf.path.transition(xs_top_in, xs_top_out, width_type='sine')
    arm_top_a = c << gf.path.extrude_transition(path_top_a, trans_top)
    arm_top_a.movey(height/2)

    # Part B: Straight merged section
    arm_top_b = c << gf.components.rectangle(size=(L_flat, w_arm_end), layer=layer, centered=False)
    # Position: x starts at L_trans. Top edge at height/2.
    arm_top_b.xmin = L_trans
    arm_top_b.ymax = height/2

    # --- 3. Bottom Arm Construction ---
    # Path lies on the bottom boundary (y = -height/2)
    path_bot_a = gf.path.straight(length=L_trans)
    
    # Offset = +width/2 keeps bottom edge on path
    s_bot_in = gf.Section(
        width=w_arm_start, 
        offset=w_arm_start/2, 
        layer=layer, 
        name="arm"
    )
    s_bot_out = gf.Section(
        width=w_arm_end, 
        offset=w_arm_end/2, 
        layer=layer, 
        name="arm"
    )
    
    xs_bot_in = gf.CrossSection(sections=[s_bot_in])
    xs_bot_out = gf.CrossSection(sections=[s_bot_out])
    
    trans_bot = gf.path.transition(xs_bot_in, xs_bot_out, width_type='sine')
    arm_bot_a = c << gf.path.extrude_transition(path_bot_a, trans_bot)
    arm_bot_a.movey(-height/2)

    # Part B: Straight merged section
    arm_bot_b = c << gf.components.rectangle(size=(L_flat, w_arm_end), layer=layer, centered=False)
    arm_bot_b.xmin = L_trans
    arm_bot_b.ymin = -height/2

    # --- Ports ---
    c.add_port("o1", port=taper.ports["o1"])
    c.add_port(
        "o2", 
        center=(L_total, 0), 
        width=height, 
        orientation=0, 
        layer=layer
    )

    return c

# Create and save
device = inverse_taper_ssc()
device.write_gds("inverse_taper_ssc.gds")