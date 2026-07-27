import gdsfactory as gf

@gf.cell
def mzi_racetrack_device():
    c = gf.Component("mzi_racetrack")
    layer = (1, 0)
    
    # --- 1. Parameters for Footprint [5.5, 3.0] ---
    total_width = 5.5
    total_height = 3.0
    
    # Frame dimensions
    # Outer Radius = total_height / 2 = 1.5
    # Straight length = total_width - 2 * Radius = 5.5 - 3.0 = 2.5
    r_outer = 1.5
    l_straight = 2.5
    frame_thickness = 0.4
    r_center = r_outer - (frame_thickness / 2) # Centerline of the frame wall
    
    # --- 2. Construct the Frame ---
    # We create a closed path for the racetrack and extrude it
    p_frame = gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_center, angle=180)
    p_frame += gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_center, angle=180)
    
    frame = gf.path.extrude(p_frame, width=frame_thickness, layer=layer)
    frame_ref = c << frame
    # Center the frame at (0,0)
    frame_ref.move((-l_straight/2, -r_center))
    
    # --- 3. Construct Junction Pads ---
    # These are the thick blocks on the far left and right inner sides
    pad_w, pad_h = 0.45, 0.7
    pad_rect = gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    
    # Position pads at the transition between arcs and straights
    lp = c << pad_rect
    lp.movex(-2.1)
    
    rp = c << pad_rect
    rp.movex(2.1)
    
    # --- 4. Construct Internal Arms (MZI) ---
    arm_w = 0.16
    arm_y_offset = 0.6
    arm_x_straight = 1.2
    
    # Define path waypoints for one arm (top) and mirror for bottom
    # From left pad to right pad
    for y_dir in [1, -1]:
        pts = [
            (-2.1, 0),
            (-1.7, 0),
            (-1.3, y_dir * arm_y_offset),
            (1.3, y_dir * arm_y_offset),
            (1.7, 0),
            (2.1, 0)
        ]
        arm_path = gf.path.smooth(pts, radius=0.4)
        c << gf.path.extrude(arm_path, width=arm_w, layer=layer)
        
        # --- 5. Add Heater Blocks ---
        # Two rectangles per arm
        heater_w, heater_h = 0.8, 0.45
        heater_gap = 0.1
        
        h1 = c << gf.components.rectangle(size=(heater_w, heater_h), layer=layer, centered=True)
        h1.move((-heater_w/2 - heater_gap/2, y_dir * arm_y_offset))
        
        h2 = c << gf.components.rectangle(size=(heater_w, heater_h), layer=layer, centered=True)
        h2.move((heater_w/2 + heater_gap/2, y_dir * arm_y_offset))

    return c

if __name__ == "__main__":
    # Create the component
    device = mzi_racetrack_device()
    
    # Save to GDS file - This ensures a file is produced regardless of viewer
    filename = "mzi_racetrack.gds"
    device.write_gds(filename)
    print(f"Success: GDS file saved as {filename}")
    
    # Optional: Try to show if a viewer is available
    try:
        device.show()
    except Exception:
        print("Note: GDS viewer not found, skipping 'show()'. Check the saved file.")