import gdsfactory as gf

@gf.cell
def trident_ssc_v4():
    """
    Trident Spot-Size Converter - Turn 4.
    
    Target Footprint: 40.0 um x 1.7 um.
    Matches the 'shoulder' flare and long central needle taper of the target.
    """
    c = gf.Component()

    # --- 1. Dimensions & Constraints ---
    L_total = 40.0
    W_total = 1.7
    
    # Center Waveguide (The Needle)
    L_center = 28.0 
    w_c_in = 0.6
    w_c_tip = 0.05
    
    # Side Arms
    w_s_in = 0.12   # Thin at the start
    w_s_out = 0.45  # Wider at the output
    gap_in = 0.1    # Gap between center and side arms at input
    
    # Flare Timing
    x_flare_start = 24.0
    x_flare_end = 35.0
    
    # Calculate Y-coordinates for side arm path
    # y_start: Center of side arm at input
    y_start = (w_c_in / 2) + gap_in + (w_s_in / 2)
    
    # y_final: Center of side arm at output to meet exactly 1.7um total height
    # Total height = 2 * (y_final + w_s_out/2) = 1.7
    y_final = (W_total / 2) - (w_s_out / 2)

    # --- 2. Center Waveguide (Taper) ---
    # A short stem followed by a long, fine taper
    stem_length = 4.0
    center_stem = c << gf.components.straight(length=stem_length, width=w_c_in)
    center_taper = c << gf.components.taper(
        length=L_center - stem_length, 
        width1=w_c_in, 
        width2=w_c_tip
    )
    center_taper.connect("o1", center_stem.ports["o2"])

    # --- 3. Side Arms (The "Shoulder" Flare) ---
    # We define a path that mimics the specific curvature of the target
    # Point 1: Origin (offset slightly in X to match target visual)
    # Point 2: End of the parallel section
    # Point 3: Mid-flare (the shoulder)
    # Point 4: Start of parallel output
    # Point 5: End of device
    pts = [
        (3.0, y_start),
        (x_flare_start, y_start),
        (x_flare_start + 6.0, y_final - 0.05), # Curvature transition
        (x_flare_end, y_final),
        (L_total, y_final)
    ]
    
    path = gf.path.smooth(points=pts, radius=10)
    
    # Define width transition: side arms widen primarily during the flare
    trans = gf.path.transition(
        cross_section1=gf.cross_section.cross_section(width=w_s_in),
        cross_section2=gf.cross_section.cross_section(width=w_s_out),
        width_type='sine' # Sine provides a smoother width ramp
    )

    # Extrude Top and Bottom Arms
    arm_top = c << gf.path.extrude_transition(path, transition=trans)
    arm_bot = c << gf.path.extrude_transition(path, transition=trans)
    arm_bot.mirror_y()

    # --- 4. Validation & Final Move ---
    # Center the component on the origin
    c.movey(-c.y)
    c.movex(-c.xmin)
    
    return c

if __name__ == "__main__":
    component = trident_ssc_v4()
    
    # Verify constraints
    print(f"Footprint: {component.xsize:.3f} x {component.ysize:.3f} um")
    
    # Save
    component.write_gds("trident_ssc_v4.gds")
    # component.show()