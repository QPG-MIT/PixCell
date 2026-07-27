import gdsfactory as gf

@gf.cell
def mzi_device_v3():
    c = gf.Component("mzi_reconstructed_v3")
    layer = (1, 0)
    
    # --- 1. Frame Construction [5.5, 3.0] ---
    # To fit 3.0 height, outer radius must be 1.5.
    # To fit 5.5 width with 1.5 radius corners, straight length = 5.5 - (2 * 1.5) = 2.5.
    r_outer = 1.5
    l_straight = 2.5
    w_frame = 0.8  # Significantly thicker frame to match target
    r_center = r_outer - w_frame/2
    
    # Path-based racetrack frame
    p_frame = gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_center, angle=180)
    p_frame += gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_center, angle=180)
    
    frame = gf.path.extrude(p_frame, width=w_frame, layer=layer)
    frame_ref = c << frame
    # Center the frame at origin
    frame_ref.move((-l_straight/2, -r_center))
    
    # --- 2. Central Junction Blocks ---
    # These are the thick horizontal bars at the left and right
    pad_w, pad_h = 0.9, 0.65
    pad_rect = gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    
    # Positions near the inner curve limits
    lp = c << pad_rect
    lp.movex(-1.8)
    
    rp = c << pad_rect
    rp.movex(1.8)
    
    # --- 3. MZI Arms ---
    # Arms branch out from the pads and contain the heater blocks
    arm_w = 0.22
    y_offset = 0.55  # Vertical separation of arms
    
    for y_sign in [1, -1]:
        # Defined to create a trapezoidal branch from the pad
        # Pad ends at +/- (1.8 - 0.45) = +/- 1.35
        pts = [
            (-1.4, 0),                       # Connect to left pad
            (-1.0, y_sign * y_offset),       # Angle up to arm height
            (1.0, y_sign * y_offset),        # Straight through heaters
            (1.4, 0)                         # Angle down to right pad
        ]
        
        # Lower radius (0.2) ensures sharper, more accurate transitions
        arm_path = gf.path.smooth(pts, radius=0.2)
        c << gf.path.extrude(arm_path, width=arm_w, layer=layer)
        
        # --- 4. Rectangular Heater Stages ---
        # Each arm has two wide blocks with a narrow vertical gap
        h_w, h_h = 0.78, 0.48
        h_gap = 0.08
        
        heater = gf.components.rectangle(size=(h_w, h_h), layer=layer, centered=True)
        
        # Left Stage
        h1 = c << heater
        h1.move((-h_w/2 - h_gap/2, y_sign * y_offset))
        
        # Right Stage
        h2 = c << heater
        h2.move((h_w/2 + h_gap/2, y_sign * y_offset))
        
    return c

if __name__ == "__main__":
    device = mzi_device_v3()
    device.write_gds("mzi_v3.gds")
    # To view in notebook: device.plot()