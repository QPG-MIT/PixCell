import gdsfactory as gf

@gf.cell
def contra_directional_coupler_corrected():
    """
    Parametric recreation of a Contra-Directional Coupler (CDC) matched to the target image.
    Features:
    - Two grated waveguides with periodic corrugations (teeth).
    - A thin central isolation line running the length of the grating.
    - Large radius input flares sweeping away from the coupling region.
    - Hairpin loopbacks on the right side returning to tapered terminations on the left.
    """
    c = gf.Component()

    # --- Parameters ---
    wg_width = 0.35
    period = 0.31            # Grating pitch
    duty_cycle = 0.5         # Fill factor
    
    # Teeth dimensions
    teeth_depth = 0.15       # Protrusion from the waveguide edge
    gap_tip_to_tip = 0.15    # Gap between the tips of opposing teeth
    
    L_grating = 18.24        # Length of the coupling region
    
    # Geometric features
    radius_loop = 1.8        # Radius of the return hairpin loops
    radius_flare = 15.0      # Large radius for the input "antenna" flares
    angle_flare = 30         # Angle of the input flares
    
    central_line_width = 0.05 # Thin line in the center

    # Layer definition
    layer_wg = (1, 0)
    
    # Cross Sections
    # FIX: Explicitly set radius to match the tightest bend (radius_loop) 
    # to prevent "min_bend_radius < CrossSection.radius_min" error.
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=layer_wg, 
        radius=radius_loop
    )
    xs_thin = gf.cross_section.cross_section(width=central_line_width, layer=layer_wg)

    # --- Helper Logic ---

    # 1. Tooth Primitive
    # Overlap allows the tooth to merge cleanly with the core.
    tooth_rect_height = teeth_depth + (wg_width / 2.0)
    
    tooth = gf.components.rectangle(
        size=(period * duty_cycle, tooth_rect_height), 
        layer=layer_wg, 
        centered=False
    )

    # 2. Calculate Vertical Positions
    # Center Y of the waveguide core needs to be offset so the tooth tips land at gap/2.
    y_offset_abs = (gap_tip_to_tip / 2.0) + tooth_rect_height

    def make_grating_arm(y_pos, invert_teeth):
        """Creates a straight waveguide with periodic teeth."""
        arm = gf.Component()
        
        # Waveguide Core
        wg = arm << gf.components.straight(length=L_grating, cross_section=xs)
        wg.movey(y_pos)
        
        # Expose ports for connection
        arm.add_port("o1", port=wg.ports["o1"])
        arm.add_port("o2", port=wg.ports["o2"])
        
        # Add Teeth
        n_teeth = int(L_grating / period)
        
        for i in range(n_teeth):
            t = arm << tooth
            x_pos = i * period
            
            if invert_teeth: 
                # Top arm: Teeth point down.
                # Placing Rect at (x, y_pos - height) aligns the bottom of the rect (tip)
                # correctly relative to the core center (y_pos).
                t.move((x_pos, y_pos - tooth_rect_height))
            else: 
                # Bottom arm: Teeth point up.
                # Placing Rect at (x, y_pos) aligns the top of the rect (tip)
                # correctly relative to the core center (y_pos).
                t.move((x_pos, y_pos))
        return arm

    # --- Construction ---

    # 1. Central Isolation Line
    # A thin straight line running exactly in the middle gap
    cline = c << gf.components.straight(length=L_grating, cross_section=xs_thin)
    
    # 2. Grating Arms
    top_grating = c << make_grating_arm(y_offset_abs, invert_teeth=True)
    bot_grating = c << make_grating_arm(-y_offset_abs, invert_teeth=False)
    
    # 3. Input Flares (Left Side)
    # Use a large radius Euler bend to create the sweeping "tail" look.
    flare = gf.components.bend_euler(radius=radius_flare, angle=angle_flare, cross_section=xs)
    
    # Top Input: Curves Up and Left
    tf = c << flare
    tf.connect("o2", top_grating.ports["o1"])
    
    # Bottom Input: Curves Down and Left
    bf = c << flare
    bf.mirror()
    bf.connect("o2", bot_grating.ports["o1"])
    
    # 4. Loopbacks (Right Side)
    # Tight circular 180-degree bends.
    loop = gf.components.bend_circular(radius=radius_loop, angle=180, cross_section=xs)
    
    # Top Loop (Curves Up)
    tl = c << loop
    tl.connect("o1", top_grating.ports["o2"])
    
    # Bottom Loop (Curves Down)
    bl = c << loop
    bl.mirror()
    bl.connect("o1", bot_grating.ports["o2"])
    
    # 5. Return Paths and Tapers
    # Straight waveguides returning to the left, extending past the flares.
    return_len = L_grating + 12.0
    
    wg_ret = gf.components.straight(length=return_len, cross_section=xs)
    taper = gf.components.taper(length=1.5, width1=wg_width, width2=0.05, cross_section=xs)
    
    # Top Return Assembly
    tr = c << wg_ret
    tr.connect("o1", tl.ports["o2"])
    tt = c << taper
    tt.connect("o1", tr.ports["o2"])
    
    # Bottom Return Assembly
    br = c << wg_ret
    br.connect("o1", bl.ports["o2"])
    bt = c << taper
    bt.connect("o1", br.ports["o2"])

    c.flatten()
    return c

if __name__ == "__main__":
    device = contra_directional_coupler_corrected()
    device.write_gds("cdc_corrected.gds")
    device.show()