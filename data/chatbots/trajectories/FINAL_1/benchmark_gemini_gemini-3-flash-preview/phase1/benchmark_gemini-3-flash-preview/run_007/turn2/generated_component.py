import gdsfactory as gf

@gf.cell
def jaw_harp_final_fixed():
    """
    Recreates the jaw-harp geometry with smooth Bezier transitions.
    Footprint constraint: 40.0 um x 1.7 um
    """
    c = gf.Component()
    LAYER = (1, 0)
    TOTAL_LENGTH = 40.0
    TOTAL_HEIGHT = 1.7
    
    # Helper function to create cross-sections with specific widths
    def get_xs(width):
        return gf.cross_section.cross_section(width=width, layer=LAYER)

    # --- 1. HANDLE (The base block on the left) ---
    l_handle = 4.0
    w_handle = 0.52
    handle = c << gf.components.rectangle(size=(l_handle, w_handle), layer=LAYER, centered=True)
    handle.xmin = 0
    handle.y = 0

    # --- 2. TONGUE (The central tapered reed) ---
    l_tongue = 22.0
    w_tip = 0.10
    # Use path extrusion for the tongue to ensure layer control and linear taper
    path_tongue = gf.path.straight(length=l_tongue)
    trans_tongue = gf.path.transition(get_xs(w_handle), get_xs(w_tip), width_type='linear')
    tongue = c << gf.path.extrude_transition(path_tongue, trans_tongue)
    # Position relative to handle
    tongue.xmin = handle.xmax
    tongue.y = 0

    # --- 3. OUTER ARMS (Smoothly flaring paths) ---
    l_arm_straight_start = 18.0   
    l_arm_flare = 12.0   
    l_arm_straight_end = 6.0    
    
    w_arm_start = 0.22
    w_arm_end = 0.48
    
    # Math to respect 1.7um height constraint:
    # Top edge of arm must be at y = 0.85 (1.7 / 2)
    # y_final_center = 0.85 - (w_arm_end / 2)
    y_final_center = (TOTAL_HEIGHT / 2) - (w_arm_end / 2) 
    y_start_center = 0.44 # Start height to maintain a clean gap with the tongue
    dy = y_final_center - y_start_center
    
    # Construct the arm path: Straight -> Bezier Flare -> Straight
    # This ensures zero curvature (flat) at the start and end of the bend
    p = gf.path.straight(length=l_arm_straight_start)
    p += gf.path.bezier(control_points=[
        (0, 0),
        (l_arm_flare * 0.5, 0),
        (l_arm_flare * 0.5, dy),
        (l_arm_flare, dy)
    ])
    p += gf.path.straight(length=l_arm_straight_end)
    
    # Define linear width transition for the arms
    trans_arm = gf.path.transition(get_xs(w_arm_start), get_xs(w_arm_end), width_type='linear')
    
    # Instantiate Top Arm
    arm_top = c << gf.path.extrude_transition(p, transition=trans_arm)
    arm_top.xmin = handle.xmax
    arm_top.movey(y_start_center)
    
    # Instantiate Bottom Arm (Mirror of top)
    arm_bot = c << gf.path.extrude_transition(p, transition=trans_arm)
    arm_bot.mirror_y()
    arm_bot.xmin = handle.xmax
    arm_bot.movey(-y_start_center)
    
    return c

if __name__ == "__main__":
    component = jaw_harp_final_fixed()
    component.show()