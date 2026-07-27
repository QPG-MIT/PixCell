import gdsfactory as gf

@gf.cell
def flared_slotted_device():
    """
    Recreates the symmetric flared slotted structure using purely parametric 
    paths, cross-sections, and boolean subtractions.
    
    The top/bottom geometries are created by drawing a solid flared block
    and then boolean-subtracting tapered horizontal slots from its center.
    This creates the complex tapering "fork" effect at the edges naturally 
    without manual polygon manipulation.
    
    Total Footprint: 120.0 x 4.0 um
    """
    c = gf.Component("flared_slotted_device")
    layer = (1, 0)

    # ---------------------------------------------------------
    # 1. Central 5 Parallel Lines
    # Spanning full length 120. Centered around y=0.
    # ---------------------------------------------------------
    xs_center = gf.cross_section.cross_section(width=0.06, layer=layer)
    for y in [0.0, 0.2, 0.4, -0.2, -0.4]:
        line = c << gf.components.straight(length=120, cross_section=xs_center)
        line.move((-60, y))

    # ---------------------------------------------------------
    # 2. Base Solid Blocks (Before Slot Subtraction)
    # These represent the solid outer boundary of the top/bottom shapes.
    # ---------------------------------------------------------
    p_taper_30 = gf.path.straight(length=30)
    p_center_60 = gf.path.straight(length=60)

    # --- Top Solid Block ---
    # Bottom edge flat at y=0.6. Top edge flares from y=1.3 to y=2.0.
    xs_top_mid = gf.cross_section.cross_section(width=0.7, offset=0.95, layer=layer)
    xs_top_end = gf.cross_section.cross_section(width=1.4, offset=1.30, layer=layer)
    
    t_top_left = gf.path.transition(xs_top_end, xs_top_mid, width_type='sine')
    t_top_right = gf.path.transition(xs_top_mid, xs_top_end, width_type='sine')
    
    c_top_left = gf.path.extrude_transition(p_taper_30, t_top_left)
    c_top_mid = gf.path.extrude(p_center_60, xs_top_mid)
    c_top_right = gf.path.extrude_transition(p_taper_30, t_top_right)
    
    top_solid = gf.Component("top_solid")
    r1 = top_solid << c_top_left
    r1.movex(-60)
    r2 = top_solid << c_top_mid
    r2.connect('o1', r1.ports['o2'])
    r3 = top_solid << c_top_right
    r3.connect('o1', r2.ports['o2'])

    # --- Bottom Solid Block ---
    # Top edge flat at y=-0.6. Bottom edge flares from y=-1.3 to y=-2.0.
    xs_bot_mid = gf.cross_section.cross_section(width=0.7, offset=-0.95, layer=layer)
    xs_bot_end = gf.cross_section.cross_section(width=1.4, offset=-1.30, layer=layer)
    
    t_bot_left = gf.path.transition(xs_bot_end, xs_bot_mid, width_type='sine')
    t_bot_right = gf.path.transition(xs_bot_mid, xs_bot_end, width_type='sine')
    
    c_bot_left = gf.path.extrude_transition(p_taper_30, t_bot_left)
    c_bot_mid_bot = gf.path.extrude(p_center_60, xs_bot_mid)
    c_bot_right = gf.path.extrude_transition(p_taper_30, t_bot_right)
    
    bot_solid = gf.Component("bot_solid")
    r1b = bot_solid << c_bot_left
    r1b.movex(-60)
    r2b = bot_solid << c_bot_mid_bot
    r2b.connect('o1', r1b.ports['o2'])
    r3b = bot_solid << c_bot_right
    r3b.connect('o1', r2b.ports['o2'])

    # ---------------------------------------------------------
    # 3. Horizontal Slots to Subtract
    # These slots are straight but taper to a point at the ends
    # to naturally form the converging solid block at x=+/-60
    # ---------------------------------------------------------
    xs_slot_mid = gf.cross_section.cross_section(width=0.1, layer=layer)
    # Microscopic width at ends to avoid topological degeneracies in booleans
    xs_slot_end = gf.cross_section.cross_section(width=0.002, layer=layer) 
    
    t_slot_left = gf.path.transition(xs_slot_end, xs_slot_mid, width_type='sine')
    t_slot_right = gf.path.transition(xs_slot_mid, xs_slot_end, width_type='sine')
    
    p_slot_taper = gf.path.straight(length=20)
    
    c_slot_left = gf.path.extrude_transition(p_slot_taper, t_slot_left)
    c_slot_mid = gf.path.extrude(p_center_60, xs_slot_mid)
    c_slot_right = gf.path.extrude_transition(p_slot_taper, t_slot_right)
    
    single_slot = gf.Component("single_slot")
    s1 = single_slot << c_slot_left
    s1.movex(-50)
    s2 = single_slot << c_slot_mid
    s2.connect('o1', s1.ports['o2'])
    s3 = single_slot << c_slot_right
    s3.connect('o1', s2.ports['o2'])
    
    # 4 horizontal slots for the top block
    top_slots = gf.Component("top_slots")
    for y_c in [0.71, 0.87, 1.03, 1.19]:
        ref = top_slots << single_slot
        ref.movey(y_c)
        
    # 4 horizontal slots for the bottom block
    bot_slots = gf.Component("bot_slots")
    for y_c in [-0.71, -0.87, -1.03, -1.19]:
        ref = bot_slots << single_slot
        ref.movey(y_c)

    # ---------------------------------------------------------
    # 4. Boolean Construction
    # "Stamp out" the tapered horizontal slots from the solid blocks
    # ---------------------------------------------------------
    top_final = gf.boolean(top_solid, top_slots, operation="not", layer=layer)
    bot_final = gf.boolean(bot_solid, bot_slots, operation="not", layer=layer)
    
    c << top_final
    c << bot_final

    return c

if __name__ == "__main__":
    device = flared_slotted_device()
    device.write_gds("flared_slotted_device.gds")