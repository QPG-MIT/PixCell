import gdsfactory as gf
import numpy as np

@gf.cell
def trident_coupler():
    """
    Creates a trident spot size converter / coupler.
    Optimized to match the visual proportions of the reference image.
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    # Constraint: Footprint dimensions
    L_total = 40.0
    H_total = 1.7
    
    # Widths (Refined from visual analysis)
    w_center_in = 0.5
    w_center_out = 0.05   # Sharp tip
    w_outer_in = 0.15     # Narrow start
    w_outer_out = 0.6     # Wide end, substantial mode expansion
    
    # Gap: very tight at input to allow mode coupling
    gap_in = 0.05          
    
    # Lengths
    # Center taper is shorter than the full device
    L_taper = 30.0
    
    # Outer arms: Significant straight section before bending
    L_straight = 15.0
    L_bend = L_total - L_straight

    # --- 1. Center Taper ---
    # Inverse taper from waveguide width to tip
    center = c << gf.components.taper(
        length=L_taper,
        width1=w_center_in,
        width2=w_center_out,
        layer=(1, 0)
    )
    center.move((0, 0))

    # --- 2. Outer Arms Geometry ---
    # Calculate Y positions to fit within footprint and gaps
    
    # Input Y center for top arm:
    # y = center_half_width + gap + outer_half_width
    y_top_in = (w_center_in / 2) + gap_in + (w_outer_in / 2)
    
    # Output Y center for top arm:
    # Constrain to the top edge of the 1.7um window
    # Top edge y = 0.85. Center = 0.85 - width/2
    y_top_out = (H_total / 2) - (w_outer_out / 2)
    
    # Vertical displacement for the S-bend
    dy = y_top_out - y_top_in

    # --- Path Generation (Straight + Adiabatic Bend) ---
    
    # A. Straight section points (y=0 relative to arm start)
    # Using small steps for straight section isn't strictly necessary but good for consistency
    points_straight = [(0.0, 0.0), (L_straight, 0.0)]
    
    # B. Bend section points (Cosine S-bend)
    # y = (dy/2) * (1 - cos(pi * t))
    # This ensures slope is 0 at start (matching straight) and 0 at end
    num_points = 101
    t = np.linspace(0, 1, num_points)
    x_bend = L_straight + t * L_bend
    y_bend = (dy / 2.0) * (1 - np.cos(np.pi * t))
    
    points_bend = np.column_stack((x_bend, y_bend))
    
    # Combine into single path
    # Drop the first point of bend to avoid duplication with end of straight
    points = np.vstack((points_straight, points_bend[1:]))
    
    p_arm = gf.Path(points)
    
    # --- Width Transition ---
    # Linear expansion from start to end
    xs_in = gf.cross_section.cross_section(width=w_outer_in, layer=(1, 0))
    xs_out = gf.cross_section.cross_section(width=w_outer_out, layer=(1, 0))
    trans = gf.path.transition(cross_section1=xs_in, cross_section2=xs_out)
    
    # --- Create Arm Component ---
    # We create the geometry once as a component to ensure symmetry
    arm_comp = gf.path.extrude_transition(p_arm, trans)
    
    # --- Placement ---
    
    # Top Arm
    # The component starts at (0,0). Move it up to starting Y.
    top_ref = c << arm_comp
    top_ref.move((0, y_top_in))
    
    # Bottom Arm
    # Mirror across X-axis, then move to negative starting Y.
    # Note: mirroring across (0,0)-(1,0) flips Y coords.
    # A point (x, y) becomes (x, -y).
    # We want the start to be at -y_top_in.
    # The component starts at (0,0). Mirrored, it's still at (0,0).
    # Moving by (0, -y_top_in) puts the start at -y_top_in.
    bot_ref = c << arm_comp
    bot_ref.mirror(p1=(0, 0), p2=(1, 0))
    bot_ref.move((0, -y_top_in))

    return c

if __name__ == "__main__":
    device = trident_coupler()
    device.write_gds("trident_coupler.gds")