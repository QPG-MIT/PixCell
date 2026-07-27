import gdsfactory as gf
import numpy as np

@gf.cell
def device_design():
    """
    Recreation of the trident spot-size converter geometry.
    Footprint constraint: 40.0 um x 1.7 um.
    """
    c = gf.Component()

    # =========================================================================
    # 1. Geometry Parameters
    # =========================================================================
    
    # Global Dimensions
    L_total = 40.0
    footprint_height = 1.7
    layer_wg = (1, 0)

    # Lengths
    # The device transitions immediately. 
    # L_transition handles the tapering and bending. L_exit handles the straight output.
    L_transition = 25.0   
    L_exit = L_total - L_transition 

    # Widths
    w_center_in = 0.6     # Center input width (wider)
    w_center_tip = 0.05   # Center tip width (sharp point)
    
    w_arm_in = 0.2        # Side arm input width (narrow)
    w_arm_out = 0.5       # Side arm output width (standard)
    
    gap_in = 0.15         # Initial gap between center and side arm
    
    # Calculate Y positions (Centers)
    # Center of top arm at input
    y_arm_in = (w_center_in / 2) + gap_in + (w_arm_in / 2)
    
    # Center of top arm at output
    # Total height 1.7 defines the outer bounds of the device.
    # Top Edge Y = 1.7 / 2 = 0.85
    # Center Y = 0.85 - (w_arm_out / 2)
    y_arm_out = (footprint_height / 2) - (w_arm_out / 2)

    # =========================================================================
    # 2. Build Central Taper
    # =========================================================================
    
    taper = c << gf.components.taper(
        length=L_transition,
        width1=w_center_in,
        width2=w_center_tip,
        layer=layer_wg
    )
    taper.move((0, 0))

    # =========================================================================
    # 3. Build Side Arms
    # =========================================================================

    def create_side_arm_geometry():
        arm = gf.Component()
        
        # --- Part 1: Transition (S-Bend + Width Taper) ---
        # Generate points for a cosine S-bend path
        n_points = 101
        t = np.linspace(0, 1, n_points)
        x_pts = t * L_transition
        
        # Cosine S-bend formula for Y coordinates
        # y(t) = y_start + (y_end - y_start) * (1 - cos(pi*t))/2
        y_pts = y_arm_in + (y_arm_out - y_arm_in) * (0.5 * (1 - np.cos(np.pi * t)))
        
        path_points = np.column_stack((x_pts, y_pts))
        p_trans = gf.Path(path_points)
        
        # Define cross-sections
        xs_in = gf.cross_section.cross_section(width=w_arm_in, layer=layer_wg)
        xs_out = gf.cross_section.cross_section(width=w_arm_out, layer=layer_wg)
        
        # Create linear width transition along the curved path
        transition = gf.path.transition(xs_in, xs_out, width_type='linear')
        
        ref_trans = arm << gf.path.extrude_transition(p_trans, transition)
        
        # --- Part 2: Straight Exit ---
        # Extrude straight output section
        p_exit = gf.path.straight(length=L_exit)
        ref_exit = arm << gf.path.extrude(p_exit, cross_section=xs_out)
        
        # Connect exit section to the end of the transition
        ref_exit.connect("o1", ref_trans.ports["o2"])
        
        return arm

    # Instantiate Top Arm
    # The geometry is generated at the correct absolute Y coordinates
    top_arm_comp = create_side_arm_geometry()
    c << top_arm_comp
    
    # Instantiate Bottom Arm
    # Reuse the same geometry but mirror across the X-axis (y=0)
    bot_ref = c << top_arm_comp
    bot_ref.mirror(p1=(0,0), p2=(1,0))

    return c

if __name__ == "__main__":
    device = device_design()
    device.write_gds("trident_coupler.gds")