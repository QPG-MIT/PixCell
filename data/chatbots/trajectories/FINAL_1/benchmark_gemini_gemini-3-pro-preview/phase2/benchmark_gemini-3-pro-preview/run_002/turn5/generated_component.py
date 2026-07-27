import gdsfactory as gf
import numpy as np

@gf.cell
def device_design():
    """
    Trident Spot-Size Converter / Inverse Taper Coupler.
    
    Features:
    - Central Waveguide: Tapers linearly from 0.5um to 0.05um (tip).
    - Side Arms: 
        1. Coupling Region: Linearly taper wider (wedge shape) while keeping the 
           inner edge parallel to the optical axis (constant gap).
        2. Fan-out Region: S-bend outwards to the final footprint separation.
    
    Constraints:
    - Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component()

    # =========================================================================
    # 1. Parameters & Dimensions
    # =========================================================================
    
    # Global Dimensions
    L_total = 40.0
    footprint_height = 1.7
    layer_wg = (1, 0)
    
    # Waveguide Widths
    w_center_in = 0.5         # Input width of center WG
    w_center_tip = 0.05       # Tip width of center WG (approx 50nm)
    
    w_arm_in = 0.05           # Tip width of side arms (start)
    w_arm_mid = 0.4           # Width of side arms at end of coupling region
    w_arm_out = 0.5           # Output width of side arms
    
    gap = 0.1                 # Gap between center WG and side WG inner edge
    
    # Longitudinal Segmentation
    # L_wedge: Length where arms expand linearly with straight inner edge
    # L_bend: Length of the S-bend fan-out
    # L_straight: Length of straight exit
    L_wedge = 20.0            
    L_bend = 15.0             
    L_straight = 5.0  # L_total - L_wedge - L_bend

    # Central Taper Length (ends slightly before or at wedge end)
    L_center_taper = 20.0

    # =========================================================================
    # 2. Central Waveguide (Inverse Taper)
    # =========================================================================
    
    taper = c << gf.components.taper(
        length=L_center_taper,
        width1=w_center_in,
        width2=w_center_tip,
        layer=layer_wg
    )
    taper.move((0, 0))

    # =========================================================================
    # 3. Side Arms Construction
    # =========================================================================
    
    def create_side_arm():
        arm = gf.Component()
        
        # --- Section A: Linear Wedge (Coupling Region) ---
        # To maintain a constant gap (straight inner edge), the center of the waveguide
        # must move outwards at half the rate of the width expansion.
        
        # Inner edge Y position (fixed)
        y_inner_fixed = (w_center_in / 2) + gap
        
        # Calculate center Y positions
        y_start = y_inner_fixed + (w_arm_in / 2)
        y_wedge_end = y_inner_fixed + (w_arm_mid / 2)
        
        # Path: Straight line
        p_wedge = gf.Path([(0, y_start), (L_wedge, y_wedge_end)])
        
        # Cross sections
        xs_in = gf.cross_section.cross_section(width=w_arm_in, layer=layer_wg)
        xs_mid = gf.cross_section.cross_section(width=w_arm_mid, layer=layer_wg)
        
        # Extrude Section A
        trans_wedge = gf.path.transition(xs_in, xs_mid, width_type='linear')
        ref_wedge = arm << gf.path.extrude_transition(p_wedge, trans_wedge)
        
        # --- Section B: S-Bend (Fan-out Region) ---
        # Calculate final Y position based on footprint
        y_final = (footprint_height / 2) - (w_arm_out / 2)
        
        # Manual Bezier Curve Generation
        # P0: Start point
        # P1: Control point 1 (horizontal from start)
        # P2: Control point 2 (horizontal from end)
        # P3: End point
        
        p0 = np.array([L_wedge, y_wedge_end])
        p3 = np.array([L_wedge + L_bend, y_final])
        
        # Control points for smooth S-bend (horizontal tangents)
        # x-offset for control points determines "aggression" of bend. 0.5 * L is standard.
        p1 = p0 + np.array([L_bend * 0.5, 0])
        p2 = p3 - np.array([L_bend * 0.5, 0])
        
        # Generate points
        t = np.linspace(0, 1, 101)
        # Cubic Bezier Formula
        bezier_x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
        bezier_y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]
        
        path_points = np.column_stack((bezier_x, bezier_y))
        p_bend = gf.Path(path_points)
        
        # Cross section for output
        xs_out = gf.cross_section.cross_section(width=w_arm_out, layer=layer_wg)
        
        # Extrude Section B
        # Use sine transition for width to match the smooth curvature
        trans_bend = gf.path.transition(xs_mid, xs_out, width_type='sine')
        ref_bend = arm << gf.path.extrude_transition(p_bend, trans_bend)
        
        # --- Section C: Straight Exit ---
        if L_straight > 0:
            p_straight = gf.Path([p3, (p3[0] + L_straight, p3[1])])
            ref_straight = arm << gf.path.extrude(p_straight, cross_section=xs_out)
        
        return arm

    # Instantiate Top Arm
    top_arm_comp = create_side_arm()
    c << top_arm_comp
    
    # Instantiate Bottom Arm (Mirror of Top Arm)
    bot_ref = c << top_arm_comp
    bot_ref.mirror()

    return c

if __name__ == "__main__":
    device = device_design()
    device.write_gds("trident_coupler.gds")