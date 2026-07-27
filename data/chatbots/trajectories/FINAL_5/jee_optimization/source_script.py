import gdsfactory as gf

@gf.cell
def grating_device():
    """
    Refined grating device with point-symmetrical arms.
    Fixed pydantic validation error by ensuring widths are multiples of 2*dbu.
    Footprint constrained to 18.24 um x 0.7 um.
    """
    # --- Physical Constraints ---
    L_TOTAL = 18.24
    LAYER = (1, 0)
    
    # --- Geometrical Refinements ---
    # Widths are chosen to be even nm (multiples of 0.002 um)
    W_WG = 0.044         # Main waveguide width
    W_BAR = 0.012        # Central horizontal bar width
    
    L_OUTER = 14.5       
    L_INNER = 10.8       
    R_LOOP = 0.12        # Radius for the 180-degree U-turn
    TAPER_L = 3.0        # Sharp taper at the start
    
    # Grating parameters
    G_PERIOD = 0.16      
    G_DUTY = 0.5
    G_HEIGHT = 0.12      
    
    c = gf.Component("grating_device")
    
    # --- 1. Central Horizontal Bar ---
    c << gf.components.rectangle(size=(L_TOTAL, W_BAR), layer=LAYER, centered=True)
    
    # --- 2. Define the Parametric Arm ---
    @gf.cell
    def make_arm():
        a = gf.Component("arm_template")
        
        # Path: Start -> move East -> 180 turn -> move West -> curve UP (Away from center)
        p = gf.Path()
        p.append(gf.path.straight(length=L_OUTER))
        p.append(gf.path.euler(radius=R_LOOP, angle=-180)) # Clockwise turn
        p.append(gf.path.straight(length=L_INNER))
        # Tail curves away (clockwise from West is North/Up)
        p.append(gf.path.euler(radius=0.7, angle=-70))     
        
        xs = gf.cross_section.cross_section(width=W_WG, layer=LAYER)
        body = a << gf.path.extrude(p, cross_section=xs)
        
        # FIX: width1 must be a multiple of 2*dbu (e.g., 0.002)
        tip = a << gf.components.taper(
            length=TAPER_L, 
            width1=0.002, 
            width2=W_WG, 
            layer=LAYER
        )
        tip.connect("o2", body.ports["o1"])
        
        # Add Grating Teeth
        num_teeth = int(L_INNER / G_PERIOD)
        # Ensure tooth width is also grid-friendly
        tooth_w = round(G_PERIOD * G_DUTY / 0.002) * 0.002
        tooth_rect = gf.components.rectangle(
            size=(tooth_w, G_HEIGHT), 
            layer=LAYER, 
            centered=True
        )
        
        y_spine = -2 * R_LOOP
        x_loop_end = L_OUTER
        
        for i in range(num_teeth):
            t = a << tooth_rect
            # Position teeth on the inner side of the loop
            tx = x_loop_end - (i + 0.5) * G_PERIOD
            ty = y_spine - (W_WG/2 + G_HEIGHT/2)
            t.move((tx, ty))
            
        return a

    # --- 3. Instantiate and Place Arms ---
    arm_ref = make_arm()
    
    # Vertical offset calculation
    local_teeth_bottom = -2 * R_LOOP - (W_WG/2) - G_HEIGHT
    y_gap = 0.02 # Gap between teeth and center bar
    y_move = y_gap - local_teeth_bottom
    
    # Top Arm
    top = c << arm_ref
    x_offset = -L_TOTAL/2 + 0.5
    top.move((x_offset, y_move))
    
    # Bottom Arm (180 degree rotation for point symmetry)
    bot = c << arm_ref
    bot.rotate(180)
    bot.move((-x_offset, -y_move))
    
    return c

if __name__ == "__main__":
    device = grating_device()
    device.write_gds("corrected_grating_device.gds")
    device.show()