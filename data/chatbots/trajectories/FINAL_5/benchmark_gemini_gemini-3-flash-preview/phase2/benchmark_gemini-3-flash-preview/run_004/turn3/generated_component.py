import gdsfactory as gf

@gf.cell
def grating_device():
    """
    Recreates the device with a central bar and two point-symmetrical arms.
    Total footprint is constrained to 18.24 um x 0.7 um.
    """
    c = gf.Component("grating_device")
    
    # --- Parameters ---
    L_TOTAL = 18.24
    LAYER = (1, 0)
    W_WG = 0.04          # Width of the main waveguide arms
    W_CENTER = 0.015     # Width of the central horizontal bar
    
    # Arm specific dimensions
    L_OUTER = 15.5       # Length of the long outer spine
    L_INNER = 12.5       # Length of the inner grating spine
    R_LOOP = 0.075       # Loop radius (determines vertical gap)
    
    # Grating parameters
    G_PERIOD = 0.16
    G_DUTY = 0.55
    G_HEIGHT = 0.065
    
    # --- 1. Central Bar ---
    # Centered at (0,0)
    c << gf.components.rectangle(size=(L_TOTAL, W_CENTER), layer=LAYER, centered=True)
    
    # --- 2. Define a Single Arm Component ---
    @gf.cell
    def make_arm():
        a = gf.Component("arm_half")
        
        # We define a path: Outer Straight -> 180 Loop -> Inner Spine -> Curved Tail
        # Vertical spacing: Outer at y=0, Inner at y = -2*R_LOOP
        y_outer = 0.0
        y_inner = -2 * R_LOOP
        
        p = gf.Path()
        p.append(gf.path.straight(length=L_OUTER))         # Goes Right (angle 0)
        p.append(gf.path.arc(radius=R_LOOP, angle=-180))   # Loops Down/Back (angle 180)
        p.append(gf.path.straight(length=L_INNER))         # Goes Left (angle 180)
        p.append(gf.path.euler(radius=0.4, angle=45))      # Curves Up/Away (angle 225)
        
        xs = gf.cross_section.cross_section(width=W_WG, layer=LAYER)
        body = a << gf.path.extrude(p, cross_section=xs)
        
        # Add tapered tip at the beginning of the outer spine
        tip = a << gf.components.taper(
            length=1.2, 
            width1=0.002, 
            width2=W_WG, 
            layer=LAYER
        )
        tip.connect("o2", body.ports["o1"])
        
        # Add periodic grating teeth on the inner spine
        # Teeth point "down" relative to the arm's orientation
        num_teeth = int(L_INNER / G_PERIOD)
        tooth_poly = gf.components.rectangle(
            size=(G_PERIOD * G_DUTY, G_HEIGHT), 
            layer=LAYER, 
            centered=True
        )
        
        # Calculate start position for grating (end of the loop)
        # Path start is at 0,0. Loop is at X=L_OUTER.
        x_start_grating = L_OUTER 
        for i in range(num_teeth):
            t = a << tooth_poly
            tx = x_start_grating - (i * G_PERIOD + G_PERIOD/2)
            ty = y_inner - (W_WG/2 + G_HEIGHT/2)
            t.move((tx, ty))
            
        return a

    # --- 3. Instantiate and Place Arms ---
    # Create one arm template
    arm_template = make_arm()
    
    # Top Arm: Positioned above the center bar
    # The arm is built with outer spine at y=0. We move it up.
    top = c << arm_template
    # Shift so inner teeth bottom is at ~y=0.03
    # Inner spine is at -0.15, teeth extend 0.065 down. Bottom is at -0.15 - 0.02 - 0.065 = -0.235
    top.movey(0.26) 
    # Center it horizontally
    top.movex(-L_TOTAL/2 + 1.2)
    
    # Bottom Arm: Rotated 180 degrees to achieve point symmetry
    bot = c << arm_template
    bot.rotate(180)
    bot.movey(-0.26)
    bot.movex(L_TOTAL/2 - 1.2)
    
    return c

if __name__ == "__main__":
    # Generate and save the layout
    device = grating_device()
    device.write_gds("improved_grating_device.gds")
    device.show()