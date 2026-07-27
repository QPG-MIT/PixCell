import gdsfactory as gf

@gf.cell
def mzi_device_v4():
    c = gf.Component("mzi_reconstructed_v4")
    layer = (1, 0)
    
    # --- 1. Footprint Constraints [5.5, 3.0] ---
    # Width = 5.5, Height = 3.0
    # For a total height of 3.0, outer radius must be 1.5.
    # Straight length = 5.5 - (2 * 1.5) = 2.5.
    r_outer = 1.5
    l_straight = 2.5
    w_frame = 0.65  # Tuned for visual match
    r_center = r_outer - w_frame/2
    
    # Path-based racetrack frame
    p_frame = gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_center, angle=180)
    p_frame += gf.path.straight(length=l_straight)
    p_frame += gf.path.arc(radius=r_center, angle=180)
    
    frame = gf.path.extrude(p_frame, width=w_frame, layer=layer)
    frame_ref = c << frame
    # Center frame at origin
    frame_ref.move(frame_ref.center).move((0,0), (0,0))
    frame_ref.center = (0,0)
    
    # --- 2. Central Connection Pads ---
    # These thick horizontal bars link the frame ends to the MZI arms
    pad_w, pad_h = 1.05, 0.62
    # Position them to overlap the inner curves (inner apex is at +/- 2.1)
    pad_x = 1.75
    
    lp = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    lp.movex(-pad_x)
    
    rp = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    rp.movex(pad_x)
    
    # --- 3. MZI Arms and Heaters ---
    arm_w = 0.22
    y_offset = 0.52 # Vertical offset for top/bottom arm centers
    
    # Heater Stage dimensions
    h_w, h_h = 0.82, 0.52
    h_gap = 0.08 # Narrow vertical slit between blocks
    
    for y_sign in [1, -1]:
        y = y_sign * y_offset
        
        # Arm path: branching out from pads, straight through heaters, then merging
        # Starts slightly inside the pad for a clean joint
        pts = [
            (-1.45, 0),
            (-0.9, y),
            (0.9, y),
            (1.45, 0)
        ]
        arm_path = gf.path.smooth(pts, radius=0.3)
        c << gf.path.extrude(arm_path, width=arm_w, layer=layer)
        
        # Left Stage Heater
        h1 = c << gf.components.rectangle(size=(h_w, h_h), layer=layer, centered=True)
        h1.move((-h_w/2 - h_gap/2, y))
        
        # Right Stage Heater
        h2 = c << gf.components.rectangle(size=(h_w, h_h), layer=layer, centered=True)
        h2.move((h_w/2 + h_gap/2, y))
        
    return c

if __name__ == "__main__":
    # Create the component
    device = mzi_device_v4()
    
    # Verify dimensions are within [3.0, 5.5]
    bbox = device.bbox()
    print(f"Device Bounding Box: {bbox}")
    
    # Write to GDS
    device.write_gds("mzi_reconstruction_v4.gds")
    # To visualize in a notebook environment, use: device.plot()