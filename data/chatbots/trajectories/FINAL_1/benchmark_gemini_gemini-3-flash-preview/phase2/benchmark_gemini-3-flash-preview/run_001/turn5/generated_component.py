import gdsfactory as gf

@gf.cell
def trident_ssc_v5():
    """
    Trident Spot-Size Converter - Turn 5.
    
    Target Footprint: 40.0 um x 1.7 um.
    Improvements: 
    - Replaced 'stem+taper' with a single sleek needle for the center.
    - Adjusted path waypoints to ensure a long parallel input section (no angle at start).
    - increased the smoothing radius and refined the transition for a 'shoulder' look.
    """
    c = gf.Component()

    # --- 1. Dimensions & Constraints ---
    L_total = 40.0
    W_total = 1.7
    
    # Center Waveguide (The Needle)
    # Starts thick, tapers to a sub-wavelength tip.
    w_c_in = 0.55
    w_c_tip = 0.06
    L_needle = 28.0 
    
    # Side Arms
    # To hit 1.7um total width: Top edge of arm must be at 0.85um (1.7/2).
    w_s_in = 0.15    # Thin input
    w_s_out = 0.45   # Thicker output
    gap_in = 0.08    # Tight initial coupling gap
    
    # Calculate Y-coordinates for the path centerlines
    # Initial: Center of needle + gap + half width of side arm
    y_start = (w_c_in / 2) + gap_in + (w_s_in / 2)
    # Final: Half of total width - half width of arm
    y_final = (W_total / 2) - (w_s_out / 2)

    # --- 2. Center Needle ---
    # Single linear taper from input to tip
    center = c << gf.components.taper(
        length=L_needle, 
        width1=w_c_in, 
        width2=w_c_tip
    )

    # --- 3. Side Arms (S-Curve Path) ---
    # Waypoints:
    # 1. (0, y_start) - The very start
    # 2. (20, y_start) - Keep parallel for half the device (crucial for target look)
    # 3. (32, y_final) - Flare out point
    # 4. (L_total, y_final) - End straight
    pts = [
        (0, y_start),
        (22.0, y_start),
        (33.0, y_final),
        (L_total, y_final)
    ]
    
    # Smooth with a large radius to eliminate kinks and create the "shoulder"
    path = gf.path.smooth(points=pts, radius=15)
    
    # Width transition: arms thicken during the flare
    trans = gf.path.transition(
        cross_section1=gf.cross_section.cross_section(width=w_s_in),
        cross_section2=gf.cross_section.cross_section(width=w_s_out),
        width_type='sine'
    )

    # Extrude Top and Bottom Arms
    arm_top = c << gf.path.extrude_transition(path, transition=trans)
    arm_bot = c << gf.path.extrude_transition(path, transition=trans)
    arm_bot.mirror_y()

    # --- 4. Final Alignment ---
    # Ensure the component is centered on (0,0) and starts at x=0
    c.movey(-c.y)
    c.movex(-c.xmin)
    
    return c

if __name__ == "__main__":
    component = trident_ssc_v5()
    
    # Print stats for verification
    print(f"Target Footprint: 40.0 x 1.7")
    print(f"Actual Footprint: {component.xsize:.3f} x {component.ysize:.3f} um")
    
    # Save output
    component.write_gds("trident_ssc_v5.gds")