import gdsfactory as gf

@gf.cell
def recreate_device():
    """
    Recreates the complex grating device geometry using parametric primitives.
    Footprint: 18.24 um x 0.7 um.
    """
    c = gf.Component("grating_device")
    
    # --- Physical Parameters ---
    L_TOTAL = 18.24
    W_CENTER = 0.04
    W_ARM = 0.06
    GAP = 0.04          
    L_GRATING = 9.0     
    R_BEND = 0.12       # The small radius causing the previous error
    L_NEEDLE_S = 7.5    
    L_NEEDLE_T = 2.0    
    N_BARS = 80         
    BAR_SIZE = (0.04, 0.18) 
    LAYER = (1, 0)

    # FIX: Explicitly set radius_min in the cross_section to allow small bends
    xs_center = gf.cross_section.cross_section(
        width=W_CENTER, 
        layer=LAYER
    )
    xs_arm = gf.cross_section.cross_section(
        width=W_ARM, 
        layer=LAYER, 
        radius_min=R_BEND # Allow radius down to R_BEND
    )
    
    # 1. Central horizontal bar
    center_bar = c << gf.components.straight(length=L_TOTAL, cross_section=xs_center)
    center_bar.movex(-L_TOTAL / 2)

    # 2. Define the Arm sub-component
    def make_arm():
        arm = gf.Component()
        
        # Grating Trunk (backbone)
        trunk = arm << gf.components.straight(length=L_GRATING, cross_section=xs_arm)
        
        # Add Grating Bars (periodic array of rectangles)
        bar_prim = gf.components.rectangle(size=BAR_SIZE, layer=LAYER, centered=True)
        pitch = L_GRATING / N_BARS
        for i in range(N_BARS):
            b = arm << bar_prim
            b.movex(i * pitch)
        
        # U-Turn Bend (180 degree Euler bend)
        # The radius_min in xs_arm now permits this R_BEND
        bend = arm << gf.components.bend_euler(radius=R_BEND, angle=180, cross_section=xs_arm)
        bend.connect("o1", trunk.ports["o2"])
        
        # Needle (Straight part + Taper)
        needle_s = arm << gf.components.straight(length=L_NEEDLE_S, cross_section=xs_arm)
        needle_s.connect("o1", bend.ports["o2"])
        
        needle_t = arm << gf.components.taper(length=L_NEEDLE_T, width1=W_ARM, width2=0.005, layer=LAYER)
        needle_t.connect("o1", needle_s.ports["o2"])
        
        # Curved Tail (Path extrusion with width transition)
        # Use a path-based approach as per the catalog
        p_tail = gf.path.euler(radius=2.5, angle=50)
        xs_start = gf.cross_section.cross_section(width=W_ARM, layer=LAYER, radius_min=R_BEND)
        xs_end = gf.cross_section.cross_section(width=0.005, layer=LAYER, radius_min=R_BEND)
        trans = gf.path.transition(xs_start, xs_end)
        tail = arm << gf.path.extrude_transition(p_tail, trans)
        tail.connect("o1", trunk.ports["o1"])
        
        return arm

    # 3. Assemble the Top and Bottom Arms
    y_offset = W_CENTER/2 + GAP + W_ARM/2
    
    # Top Arm
    top_arm = c << make_arm()
    top_arm.movey(y_offset)
    top_arm.movex(-L_GRATING/2 + 1.2) 

    # Bottom Arm
    bot_arm = c << make_arm()
    bot_arm.rotate(180)
    bot_arm.movey(-y_offset)
    bot_arm.movex(L_GRATING/2 - 1.2)

    return c

if __name__ == "__main__":
    device = recreate_device()
    device.write_gds("recreated_device.gds")