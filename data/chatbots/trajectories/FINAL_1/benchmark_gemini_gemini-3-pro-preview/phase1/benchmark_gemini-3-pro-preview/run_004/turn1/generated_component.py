import gdsfactory as gf

@gf.cell
def inverse_taper_ssc():
    c = gf.Component()

    # --- Dimensions ---
    length = 40.0
    height = 1.7
    layer = (1, 0)

    # --- 1. Central Taper ---
    # Tapers from 0.6um to 0.05um, ending partway through the device (25um)
    taper = c << gf.components.taper(
        length=25.0,
        width1=0.6,
        width2=0.05,
        layer=layer
    )
    # Taper is centered at (0,0) by default

    # --- 2. Outer Arms Construction ---
    # To create the cladding arms that have a straight outer edge and a curved inner edge,
    # we define a straight path at the device boundary and use a transition that
    # varies both width and offset.
    
    w_arm_start = 0.2
    w_arm_end = height / 2.0  # 0.85 (Half the total height to merge fully)

    # -- Top Arm Configuration (Path at y = +height/2) --
    # Offset = -width/2 ensures the top edge of the waveguide stays on the path
    s_top_in = gf.Section(
        width=w_arm_start, 
        offset=-w_arm_start/2, 
        layer=layer, 
        name="main_arm"  # REQUIRED: Name must match in both sections
    )
    s_top_out = gf.Section(
        width=w_arm_end, 
        offset=-w_arm_end/2, 
        layer=layer, 
        name="main_arm"
    )
    
    xs_top_in = gf.CrossSection(sections=[s_top_in])
    xs_top_out = gf.CrossSection(sections=[s_top_out])
    
    # 'sine' width_type creates the smooth S-bend profile on the inner edge
    trans_top = gf.path.transition(xs_top_in, xs_top_out, width_type='sine')
    
    path_top = gf.path.straight(length=length)
    arm_top = c << gf.path.extrude_transition(path_top, trans_top)
    arm_top.movey(height/2) # Move path to top boundary

    # -- Bottom Arm Configuration (Path at y = -height/2) --
    # Offset = +width/2 ensures the bottom edge of the waveguide stays on the path
    s_bot_in = gf.Section(
        width=w_arm_start, 
        offset=w_arm_start/2, 
        layer=layer, 
        name="main_arm" # Matching name
    )
    s_bot_out = gf.Section(
        width=w_arm_end, 
        offset=w_arm_end/2, 
        layer=layer, 
        name="main_arm"
    )
    
    xs_bot_in = gf.CrossSection(sections=[s_bot_in])
    xs_bot_out = gf.CrossSection(sections=[s_bot_out])
    
    trans_bot = gf.path.transition(xs_bot_in, xs_bot_out, width_type='sine')
    
    path_bot = gf.path.straight(length=length)
    arm_bot = c << gf.path.extrude_transition(path_bot, trans_bot)
    arm_bot.movey(-height/2) # Move path to bottom boundary

    return c

# Create and save
device = inverse_taper_ssc()
device.write_gds("inverse_taper_ssc.gds")