import gdsfactory as gf

@gf.cell
def grating_coupler_device():
    """
    Recreates the device geometry within a 18.24um x 0.7um footprint.
    
    Fixes:
    1. radius_min: Explicitly sets a low radius_min in the cross-section to allow 0.09um bends.
    2. Symmetry: Sets taper tip to 0.002um (2 DBU) to satisfy grid symmetry requirements.
    """
    c = gf.Component("grating_device")
    
    # --- Geometric Parameters ---
    L_TOTAL = 18.24
    W_WG = 0.08         # 80 nm waveguide width
    W_CENTER = 0.02     # 20 nm central line
    W_TAPER_TIP = 0.002 # 2 nm tip (Must be multiple of 2 DBU)
    
    # Vertical distribution to fit 0.7um height
    # Total span: outer_edge - (-outer_edge) = (0.31+0.04) - (-0.35) = 0.7 um
    Y_OUTER = 0.31
    Y_INNER = 0.13
    R_BEND = (Y_OUTER - Y_INNER) / 2  # Calculated radius = 0.09 um
    
    # --- Define Cross Section ---
    # We override radius_min to allow the small bends required for this sub-micron device
    xs = gf.cross_section.cross_section(
        width=W_WG, 
        layer=(1, 0), 
        radius_min=0.01  # Set lower than 0.09 to allow the loop
    )
    
    # --- 1. Central Separator ---
    c << gf.components.rectangle(size=(L_TOTAL, W_CENTER), layer=(1, 0), centered=True)
    
    def add_arm_half(is_top=True):
        sign = 1 if is_top else -1
        
        # --- 2. Outer Tapered Arm ---
        # Starts from the left side
        l_outer = L_TOTAL - R_BEND - 0.2
        outer_arm = c << gf.components.taper(
            length=l_outer,
            width1=W_TAPER_TIP,
            width2=W_WG,
            layer=(1, 0)
        )
        outer_arm.move((l_outer/2, sign * Y_OUTER))
        
        # --- 3. 180-degree Loop ---
        # Connects outer arm to inner arm. Uses the custom cross_section.
        bend = c << gf.components.bend_circular(
            radius=R_BEND,
            angle=180,
            cross_section=xs
        )
        bend.connect("o1", outer_arm.ports["o2"])
        
        # --- 4. Inner Grating Arm ---
        period = 0.22
        duty_cycle = 0.5
        w_tooth = period * duty_cycle
        num_periods = 55 
        
        # Build grating segments from the loop output towards the left
        current_x = bend.ports["o2"].center[0]
        last_tooth_port = None
        
        for i in range(num_periods):
            tooth = c << gf.components.straight(
                length=w_tooth,
                cross_section=xs
            )
            # Position to maintain periodic gap
            x_pos = current_x - (i * period) - w_tooth/2
            tooth.move((x_pos, sign * Y_INNER))
            last_tooth_port = tooth.ports["o1"]
            
        # --- 5. Curved Tail ---
        # The adiabatic exit tail at the far left of the grating
        tail = c << gf.components.bend_euler(
            radius=4.0, 
            angle=-sign * 55, 
            p=0.5,
            cross_section=xs
        )
        tail.connect("o1", last_tooth_port)

    # Generate both symmetrical halves
    add_arm_half(is_top=True)
    add_arm_half(is_top=False)
    
    return c

if __name__ == "__main__":
    device = grating_coupler_device()
    device.write_gds("grating_device_final.gds")
    device.show()