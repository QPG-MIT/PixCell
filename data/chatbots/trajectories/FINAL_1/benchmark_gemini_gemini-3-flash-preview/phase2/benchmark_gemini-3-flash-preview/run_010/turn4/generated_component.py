import gdsfactory as gf
import numpy as np

@gf.cell
def recreate_device():
    """
    Trident Coupler
    Constraint: 40.0um x 1.7um
    
    Fix: Side arms are created as single continuous paths to avoid 
    off-grid instance errors caused by port connections.
    """
    c = gf.Component("trident_coupler_v7")
    LAYER = (1, 0)

    # --- Dimensions ---
    L_TOTAL = 40.0
    H_MAX = 1.7
    
    # Central Waveguide (stays on-axis)
    w_center_in = 0.60
    l_center = 26.0
    
    # Side Arm parameters
    l_straight = 28.0
    l_flare = 12.0  # 28 + 12 = 40.0
    w_arm_in = 0.12
    w_arm_out = 0.50
    
    # Vertical positions (center-to-center)
    y_arm_start = 0.46 
    y_arm_end = 0.60   # (0.60 + 0.5/2) * 2 = 1.7um total height
    
    # 1. Central Waveguide (Taper)
    c << gf.components.taper(
        length=l_center,
        width1=w_center_in,
        width2=0.01,
        layer=LAYER
    )

    # 2. Side Arms (Symmetric)
    def add_arm(is_top=True):
        sign = 1 if is_top else -1
        
        # Create a single continuous path
        # Part 1: Straight section
        x_straight = np.linspace(0, l_straight, 20)
        y_straight = np.full_like(x_straight, sign * y_arm_start)
        
        # Part 2: S-bend Flare section
        x_flare_rel = np.linspace(0, l_flare, 30)
        dy = (y_arm_end - y_arm_start)
        # Smooth cosine transition
        y_flare_rel = sign * (dy * 0.5 * (1 - np.cos(np.pi * x_flare_rel / l_flare)))
        
        x_pts = np.concatenate([x_straight, l_straight + x_flare_rel[1:]])
        y_pts = np.concatenate([y_straight, sign * y_arm_start + y_flare_rel[1:]])
        
        arm_path = gf.Path(np.column_stack([x_pts, y_pts]))
        
        # Define the width transition over the whole length
        # We keep it thin for the straight part, then expand in the flare
        # To do this precisely, we use cross_section.section
        xs = gf.CrossSection(
            sections=[
                gf.Section(width=w_arm_in, offset=0, layer=LAYER, name="main", port_names=("o1", "o2"))
            ]
        )
        
        # Transition from thin to thick
        xs_start = gf.cross_section.cross_section(width=w_arm_in, layer=LAYER)
        xs_end = gf.cross_section.cross_section(width=w_arm_out, layer=LAYER)
        
        # Extrude with transition
        # Note: In a single path, the transition interpolates from start to end.
        # This matches the target visual where the arm thickens as it flares.
        arm_ref = c << gf.path.extrude_transition(
            arm_path, 
            transition=gf.path.transition(xs_start, xs_end, width_type='linear')
        )

    add_arm(is_top=True)
    add_arm(is_top=False)

    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_device()
    
    # Verification of constraints
    print(f"Target Dimensions: 40.0 um x 1.7 um")
    print(f"Result Dimensions: {device.xsize:.2f} um x {device.ysize:.2f} um")
    
    # Save to GDS
    device.write_gds("trident_coupler_v7.gds")