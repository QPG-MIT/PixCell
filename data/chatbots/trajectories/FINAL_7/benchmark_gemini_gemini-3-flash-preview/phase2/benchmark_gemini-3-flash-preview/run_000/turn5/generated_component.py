import gdsfactory as gf

@gf.cell
def mzi_reconstructed_v7():
    c = gf.Component("mzi_v7")
    layer = (1, 0)
    
    # --- 1. Footprint & Frame [5.5 x 3.0] ---
    # Width=5.5, Height=3.0 -> Outer radius must be 1.5.
    # Straight section = 5.5 - (2 * 1.5) = 2.5.
    r_outer = 1.5
    l_straight = 2.5
    w_frame = 0.7  # Matches the visual weight of the original racetrack
    
    # Create racetrack frame centered at (0,0)
    p_frame = gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_outer - w_frame/2, angle=180)
    p_frame += gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_outer - w_frame/2, angle=180)
    
    frame = gf.path.extrude(p_frame, width=w_frame, layer=layer)
    fr_ref = c << frame
    fr_ref.center = (0, 0)
    
    # --- 2. Feeder Pads (Horizontal connectors) ---
    # These link the frame ends to the internal MZI arms
    pad_w, pad_h = 1.1, 0.58
    pad_x_center = 1.75
    
    lp = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    lp.movex(-pad_x_center)
    
    rp = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    rp.movex(pad_x_center)
    
    # --- 3. MZI Shifter Blocks & Arms ---
    arm_w = 0.22
    y_offset = 0.6  # Vertical separation for top and bottom arms
    
    # Heater stage consists of two rectangles per arm with a small gap
    block_w, block_h = 0.82, 0.52
    block_gap = 0.08 # Narrow vertical line from the original image
    
    for y_sign in [1, -1]:
        y = y_sign * y_offset
        
        # Place the two-part shifter blocks
        b1 = c << gf.components.rectangle(size=(block_w, block_h), layer=layer, centered=True)
        b1.move((-block_w/2 - block_gap/2, y))
        
        b2 = c << gf.components.rectangle(size=(block_w, block_h), layer=layer, centered=True)
        b2.move((block_w/2 + block_gap/2, y))
        
        # --- Smooth Branching Paths ---
        # Radius 0.1 is safe for these waypoint distances (>0.3um)
        
        # Left side split: Pad -> Heater
        pts_l = [
            (-1.5, 0),  # Start inside the feeder pad
            (-1.1, 0),  # Point before the fork
            (-0.8, y)   # Entry to the heater block
        ]
        path_l = gf.path.smooth(pts_l, radius=0.1)
        c << gf.path.extrude(path_l, width=arm_w, layer=layer)
        
        # Right side merge: Heater -> Pad
        pts_r = [
            (0.8, y),   # Exit from the heater block
            (1.1, 0),   # Point after convergence
            (1.5, 0)    # Finish inside the feeder pad
        ]
        path_r = gf.path.smooth(pts_r, radius=0.1)
        c << gf.path.extrude(path_r, width=arm_w, layer=layer)
        
    return c

if __name__ == "__main__":
    # Instantiate component
    device = mzi_reconstructed_v7()
    
    # Corrected footprint verification (avoids 'DBox is not subscriptable' error)
    w = device.dxsize
    h = device.dysize
    print(f"Validated Dimensions: {w:.2f} um x {h:.2f} um")
    
    # Export
    device.write_gds("mzi_reconstruction_v7.gds")