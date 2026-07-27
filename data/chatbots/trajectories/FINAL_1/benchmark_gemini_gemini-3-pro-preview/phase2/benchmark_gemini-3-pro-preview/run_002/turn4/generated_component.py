import gdsfactory as gf
import numpy as np

@gf.cell
def device_design():
    """
    Trident Spot-Size Converter / Inverse Taper Coupler.
    
    Features:
    - Central waveguide tapers linearly to a fine tip.
    - Two side arms start as sharp tips close to the center and expand outwards.
    - Side arms use a calculated cubic spline path. This ensures the inner edge 
      remains straight (wedge-like) in the coupling region by matching the 
      path slope to the width expansion rate, eliminating the "belly" seen in standard S-bends.
    
    Constraints:
    - Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component()

    # =========================================================================
    # 1. Geometry Parameters
    # =========================================================================
    
    # Global Dimensions
    L_total = 40.0
    L_transition = 25.0       # Length of the tapered/bending section
    L_exit = L_total - L_transition # Length of the straight output section
    
    footprint_height = 1.7    # Outer edge to outer edge distance at output
    layer_wg = (1, 0)

    # Waveguide Widths
    w_center_in = 0.5         # Input width of central waveguide
    w_center_tip = 0.05       # Tip width of central waveguide (terminates)
    
    w_arm_in = 0.05           # Input width of side arms (sharp tip)
    w_arm_out = 0.5           # Output width of side arms
    
    gap_in = 0.1              # Initial gap between central waveguide and side arms

    # Y-Position Calculations
    # -----------------------
    # Output: Arms are pushed to the edges of the 1.7um footprint.
    # Center Y = (Height/2) - (Width/2)
    y_arm_out = (footprint_height / 2) - (w_arm_out / 2)
    
    # Input: Arms are tightly packed against the central waveguide.
    # Center Y = (Center_Width/2) + Gap + (Arm_Width/2)
    y_arm_in = (w_center_in / 2) + gap_in + (w_arm_in / 2)

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
    # 3. Build Side Arms (Cubic Spline Path)
    # =========================================================================

    def create_side_arm():
        arm = gf.Component()
        
        # --- Path Derivation ---
        # We need a path y(x) that:
        # 1. Starts at y_arm_in with a slope that counteracts the width expansion
        #    so the inner edge stays flat/parallel to the axis initially.
        # 2. Ends at y_arm_out with a slope of 0 (parallel output).
        
        L = L_transition
        dy = y_arm_out - y_arm_in
        
        # Calculate width expansion rate (per side)
        # The inner edge position is y_center(x) - w(x)/2.
        # To keep inner edge slope ~ 0, we need y'_center(x) = w'(x)/2.
        w_growth_total = w_arm_out - w_arm_in
        slope_initial = (w_growth_total / L) / 2
        
        # Cubic Polynomial y(x) = a + bx + cx^2 + dx^3
        # Constraints:
        # y(0) = y_arm_in
        # y'(0) = slope_initial
        # y(L) = y_arm_out
        # y'(L) = 0
        
        # Coefficients derived from boundary conditions:
        a = y_arm_in
        b = slope_initial
        # Solving for c and d:
        # c*L^2 + d*L^3 = dy - b*L
        # 2*c*L + 3*d*L^2 = -b
        
        c_coeff = (3 * dy - 2 * b * L) / (L**2)
        d_coeff = (-b - 2 * c_coeff * L) / (3 * L**2)
        
        # Generate Path Points
        n_points = 101
        x_pts = np.linspace(0, L, n_points)
        y_pts = a + b * x_pts + c_coeff * x_pts**2 + d_coeff * x_pts**3
        
        path_points = np.column_stack((x_pts, y_pts))
        p_trans = gf.Path(path_points)
        
        # Define Cross Sections
        xs_in = gf.cross_section.cross_section(width=w_arm_in, layer=layer_wg)
        xs_out = gf.cross_section.cross_section(width=w_arm_out, layer=layer_wg)
        
        # Extrude Transition
        transition = gf.path.transition(xs_in, xs_out, width_type='linear')
        ref_trans = arm << gf.path.extrude_transition(p_trans, transition)
        
        # --- Straight Exit ---
        p_exit = gf.path.straight(length=L_exit)
        ref_exit = arm << gf.path.extrude(p_exit, cross_section=xs_out)
        
        # Connect exit to transition
        ref_exit.connect("o1", ref_trans.ports["o2"])
        
        return arm

    # Instantiate Top Arm
    top_arm_comp = create_side_arm()
    c << top_arm_comp
    
    # Instantiate Bottom Arm (Mirror of Top Arm)
    bot_ref = c << top_arm_comp
    bot_ref.mirror(p1=(0,0), p2=(1,0))

    return c

if __name__ == "__main__":
    device = device_design()
    device.write_gds("trident_coupler.gds")