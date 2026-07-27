import gdsfactory as gf
import math

# Use check_instances=False to bypass strict grid checks for custom path connections
@gf.cell(check_instances=False)
def recreate_device():
    """
    Recreates the tapered trident coupler geometry.
    
    Features:
    - Central waveguide: Starts wide, tapers to a sharp point.
    - Side arms: Start thin, widen while straight, and continue to widen while curving.
    - Dimensions: Strictly adheres to [40.0, 1.7] um.
    """
    c = gf.Component("tapered_trident")

    # --- Dimensions ---
    L_TOTAL = 40.0
    H_MAX = 1.7
    
    # 1. Central Waveguide (Taper to sharp point)
    # Ends before the side arms reach their maximum curvature
    l_center = 26.0
    w_center_base = 0.5
    center = c << gf.components.taper(
        length=l_center, 
        width1=w_center_base, 
        width2=0.005, 
        layer=(1, 0)
    )
    center.movey(0)

    # 2. Outer Arm Parameters
    l_straight = 22.0
    l_curve = L_TOTAL - l_straight # 18.0 um
    
    # Progressive widths: thin (start) -> medium (mid-bend) -> wide (end)
    w_start = 0.15
    w_mid = 0.32
    w_end = 0.48
    
    # Vertical offsets (center-to-center)
    # y_final + w_end/2 must be <= 0.85 (half of 1.7um height)
    y_init = 0.42 
    y_final = 0.61 # 0.61 + 0.24 = 0.85
    dy = y_final - y_init

    # Cross-sections for smooth curve transition
    xs_mid = gf.cross_section.cross_section(width=w_mid, layer=(1, 0))
    xs_end = gf.cross_section.cross_section(width=w_end, layer=(1, 0))
    trans = gf.path.transition(xs_mid, xs_end, width_type='sine')

    def add_side_arm(is_top=True):
        sign = 1 if is_top else -1
        
        # A. Straight Taper section
        straight = c << gf.components.taper(
            length=l_straight,
            width1=w_start,
            width2=w_mid,
            layer=(1, 0)
        )
        straight.movey(sign * y_init)
        
        # B. Curved Taper section (Manual S-bend Path)
        pts = []
        n_pts = 40
        for i in range(n_pts + 1):
            x = i * l_curve / n_pts
            # Smooth S-bend profile: y = dy/2 * (1 - cos(pi * x / L))
            y = sign * (dy / 2.0) * (1.0 - math.cos(math.pi * x / l_curve))
            pts.append((x, y))
        
        p = gf.Path(pts)
        curve = c << gf.path.extrude_transition(p, transition=trans)
        
        # Connect to the straight segment
        curve.connect("o1", straight.ports["o2"])

    # Create symmetric arms
    add_side_arm(is_top=True)
    add_side_arm(is_top=False)

    # Flattening ensures all coordinates snap to the nearest grid point for the GDS
    c.flatten()
    return c

if __name__ == "__main__":
    device = recreate_device()
    
    # Verification
    print(f"Final Footprint: {device.xsize:.2f} um x {device.ysize:.2f} um")
    
    # Export GDS file
    gds_name = "tapered_trident_coupler.gds"
    device.write_gds(gds_name)
    print(f"Success: GDS file '{gds_name}' has been created.")
    
    # Visualize if environment permits
    # device.show()