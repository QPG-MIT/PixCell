import gdsfactory as gf
import math

@gf.cell
def recreate_device_v3_final():
    """
    Turn 3: High-fidelity reconstruction.
    Uses custom path points to ensure compatibility and smooth geometry.
    Matches the tapered side arms and sharp central needle of the target.
    Footprint: 40.0um x 1.7um.
    """
    c = gf.Component("refined_target_device")
    
    # 1. Global Constraints
    L_TOTAL = 40.0
    H_TOTAL = 1.7
    LAYER = (1, 0)
    
    # 2. Middle Arm (Central Needle)
    # Starts at X=0, Y=0. Long taper for sharp profile.
    W_MID_BASE = 0.36
    L_MID_STRAIGHT = 7.0
    L_MID_TAPER = 28.0 
    
    mid_xs = gf.cross_section.cross_section(width=W_MID_BASE, layer=LAYER)
    m_straight = c << gf.components.straight(length=L_MID_STRAIGHT, cross_section=mid_xs)
    # Tapering to 1nm (0.001um) creates the sharp point seen in the image
    m_taper = c << gf.components.taper(length=L_MID_TAPER, width1=W_MID_BASE, width2=0.001, layer=LAYER)
    m_taper.connect("o1", m_straight.ports["o2"])
    
    # 3. Side Arms (Tapered and Curved)
    X_INDENT = 3.8      # Indented from the far left
    W_SIDE_IN = 0.12    # Thin start
    W_SIDE_OUT = 0.50   # Thick end
    GAP_INIT = 0.12     # Gap between needle and side arms at start
    
    # Calculate Y-offsets for footprint (Center-to-Center)
    y_start = (W_MID_BASE / 2) + GAP_INIT + (W_SIDE_IN / 2)
    y_final = (H_TOTAL / 2) - (W_SIDE_OUT / 2)
    dy = y_final - y_start
    
    # Create the smooth flare path manually to ensure compatibility
    L_SIDE_PATH = L_TOTAL - X_INDENT
    num_pts = 40
    pts = []
    for i in range(num_pts):
        x = (i / (num_pts - 1)) * L_SIDE_PATH
        # Smoothstep flare formula for the S-bend shape
        # Flare begins after 15um and ends near 35um
        x_norm = max(0, min(1, (x - 12.0) / 20.0))
        y = dy * (3 * x_norm**2 - 2 * x_norm**3)
        pts.append((x, y))
    
    # Define Path and Transition
    side_path = gf.Path(pts)
    xs_start = gf.cross_section.cross_section(width=W_SIDE_IN, layer=LAYER)
    xs_end = gf.cross_section.cross_section(width=W_SIDE_OUT, layer=LAYER)
    trans = gf.path.transition(xs_start, xs_end, width_type='linear')
    
    # Extrude side arm geometry
    side_arm_comp = gf.path.extrude_transition(side_path, trans)
    
    # Add Top Arm
    top = c << side_arm_comp
    top.move((X_INDENT, y_start))
    
    # Add Bottom Arm (Symmetrical)
    bot = c << side_arm_comp
    bot.mirror(p1=(0, 0), p2=(1, 0))
    bot.move((X_INDENT, -y_start))
    
    return c

if __name__ == "__main__":
    device = recreate_device_v3_final()
    
    # Verification of dimensions
    print(f"Final Footprint Verification:")
    print(f"Width:  {device.dxsize:.2f} um (Target: 40.0)")
    print(f"Height: {device.dysize:.2f} um (Target: 1.7)")
    
    device.write_gds("device_v3_final.gds")