import gdsfactory as gf

@gf.cell
def trident_spot_size_converter():
    """
    Recreates the Trident SSC from the image.
    Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component("trident_ssc")
    layer = (1, 0)
    
    # 1. Parameters for geometry and footprint
    L_total = 40.0
    W_total = 1.7
    
    # Input section (left-most thick part)
    L_in = 5.0
    W_in = 0.9
    
    # Middle branch (tapers to a narrow point)
    L_mid = 20.0
    W_mid_start = 0.4
    W_mid_end = 0.05
    
    # Side arms parameters
    L_arm_total = L_total - L_in  # 35.0 um
    W_arm_start = 0.25
    W_arm_end = 0.45
    
    # Vertical placement to meet 1.7um width constraint
    # Arm edge should be at y = +/- 0.85
    # y_final + W_arm_end/2 = 0.85 => y_final = 0.625
    y_start = 0.35 
    y_final = 0.625
    dy = y_final - y_start
    
    # 2. Build the Common Input Trunk
    trunk = c << gf.components.straight(length=L_in, width=W_in, layer=layer)
    trunk.movex(L_in / 2) # Position from x=0 to x=5
    
    # 3. Build the Middle Taper Branch
    mid_branch = c << gf.components.taper(
        length=L_mid, 
        width1=W_mid_start, 
        width2=W_mid_end, 
        layer=layer
    )
    mid_branch.movex(L_in + L_mid / 2) # Starts at x=5
    
    # 4. Build Outer Arms using Path Extrusion
    # Define waypoints for a smooth S-bend transition
    pts = [
        (0, 0), 
        (10, 0),          # Start parallel
        (25, dy),         # Bend outward
        (L_arm_total, dy) # End parallel
    ]
    
    # Create smooth path with radius (radius=5.0 is safe for these lengths)
    arm_path = gf.path.smooth(points=pts, radius=5.0)
    
    # Define the width transition (tapering from narrow base to wide tip)
    xs_start = gf.cross_section.cross_section(width=W_arm_start, layer=layer)
    xs_end = gf.cross_section.cross_section(width=W_arm_end, layer=layer)
    arm_trans = gf.path.transition(xs_start, xs_end)
    
    # Instantiate Top Arm
    top_arm = c << gf.path.extrude_transition(arm_path, transition=arm_trans)
    top_arm.move((L_in, y_start))
    
    # Instantiate Bottom Arm (Mirrored)
    bot_arm = c << gf.path.extrude_transition(arm_path, transition=arm_trans)
    bot_arm.mirror_y()
    bot_arm.move((L_in, -y_start))
    
    return c

if __name__ == "__main__":
    # Clear any previous cache
    gf.clear_cache()
    
    # Create the device
    device = trident_spot_size_converter()
    
    # EXPLICITLY SAVE THE GDS FILE
    output_filename = "trident_ssc.gds"
    device.write_gds(output_filename)
    
    print(f"Success! The GDS file '{output_filename}' has been created in your directory.")
    
    # Attempt to open viewer if available
    try:
        device.show()
    except Exception:
        print("KLayout viewer not found; use 'trident_ssc.gds' in your preferred editor.")