import gdsfactory as gf

@gf.cell
def mzi_device_reconstructed():
    c = gf.Component("mzi_reconstructed")
    layer = (1, 0)
    
    # --- 1. Footprint & Frame Construction [5.5, 3.0] ---
    # Total height 3.0 -> r_outer = 1.5
    # Total width 5.5 -> straight_len = 5.5 - (2 * 1.5) = 2.5
    r_outer = 1.5
    l_straight = 2.5
    w_frame = 0.42
    r_center = r_outer - w_frame/2
    
    # Define the frame path with high point density for smoothness
    p_frame = gf.path.straight(length=l_straight)
    # npoints here ensures the curve is not faceted
    p_frame += gf.path.arc(radius=r_center, angle=180, npoints=150)
    p_frame += gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_center, angle=180, npoints=150)
    
    frame = gf.path.extrude(p_frame, width=w_frame, layer=layer)
    frame_ref = c << frame
    frame_ref.move((-l_straight/2, -r_center))
    
    # --- 2. Junction Pads (Splitter/Combiner Blocks) ---
    pad_w, pad_h = 0.7, 0.45
    pad_rect = gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    
    # Position pads where the arms merge
    lp = c << pad_rect
    lp.movex(-1.85)
    
    rp = c << pad_rect
    rp.movex(1.85)
    
    # --- 3. MZI Arms with Convergent Junctions ---
    arm_w = 0.16
    y_offset = 0.62  # Vertical distance for the horizontal arms
    
    # Create top and bottom arms
    for y_sign in [1, -1]:
        # Defining waypoints that converge to (x, 0) creates the 'Y' wedge
        pts = [
            (-1.85, 0),                      # Start at center of left pad
            (-1.45, y_sign * 0.1),            # Diagonal divergence
            (-1.1, y_sign * y_offset),       # Reach heater height
            (1.1, y_sign * y_offset),        # Horizontal arm segment
            (1.45, y_sign * 0.1),             # Diagonal convergence
            (1.85, 0)                        # End at center of right pad
        ]
        
        # Create a smooth adiabatic path
        arm_path = gf.path.smooth(pts, radius=0.4)
        c << gf.path.extrude(arm_path, width=arm_w, layer=layer)
        
        # --- 4. Dual Heater Stages ---
        heater_w = 0.82
        heater_h = 0.45
        heater_gap = 0.12
        
        # Stage 1 Heater
        h1 = c << gf.components.rectangle(size=(heater_w, heater_h), layer=layer, centered=True)
        h1.move((-heater_w/2 - heater_gap/2, y_sign * y_offset))
        
        # Stage 2 Heater
        h2 = c << gf.components.rectangle(size=(heater_w, heater_h), layer=layer, centered=True)
        h2.move((heater_w/2 + heater_gap/2, y_sign * y_offset))
        
    return c

if __name__ == "__main__":
    # Create the component
    device = mzi_device_reconstructed()
    
    # Write the GDS file
    device.write_gds("mzi_final_reconstruction.gds")
    print("Success: 'mzi_final_reconstruction.gds' generated.")