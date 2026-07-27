import gdsfactory as gf
import numpy as np

@gf.cell
def trident_coupler():
    """
    Creates a trident spot size converter / coupler.
    Matches the topology of a central input taper flanked by two expanding outer arms.
    The outer arms remain parallel to the center taper before bending outwards.
    """
    c = gf.Component()

    # --- Geometric Constraints & Parameters ---
    # Constraint: Footprint dimensions
    L_total = 40.0
    H_total = 1.7
    
    # Lengths
    # The center taper handles the mode conversion. 
    # The outer arms stay straight alongside it, then bend out.
    L_taper_center = 25.0
    L_straight_outer = 25.0  # Matched to center taper length
    L_bend_outer = L_total - L_straight_outer # 15.0

    # Waveguide Widths
    w_center_in = 0.5
    w_center_out = 0.05  # Tapers to a sharp tip
    
    w_outer_in = 0.15    # Starts narrow
    w_outer_out = 0.6    # Ends wide for mode expansion
    
    # Gap
    gap_in = 0.05        # Tight gap for coupling
    
    # --- 1. Center Taper ---
    # Linear taper from input width to tip
    center = c << gf.components.taper(
        length=L_taper_center,
        width1=w_center_in,
        width2=w_center_out,
        layer=(1, 0)
    )
    center.move((0, 0))

    # --- 2. Outer Arms Geometry ---
    
    # Calculate Y positions
    # Input Y (center of top arm):
    # Center WG half-width + Gap + Outer WG half-width
    y_top_in = (w_center_in / 2.0) + gap_in + (w_outer_in / 2.0)
    
    # Output Y (center of top arm):
    # Constrained by total height H_total. 
    # Top edge = H_total/2. Center = Top edge - half-width.
    y_top_out = (H_total / 2.0) - (w_outer_out / 2.0)
    
    # Vertical displacement for the bend section
    dy = y_top_out - y_top_in
    
    # -- Path Generation --
    # We construct the path manually to control the straight-then-bend profile exactly.
    
    # Section A: Straight (Parallel to center)
    x_straight = np.linspace(0, L_straight_outer, 2)
    y_straight = np.zeros_like(x_straight)
    
    # Section B: Cosine S-Bend (Flaring out)
    # Generates a smooth S-curve from (0,0) to (L_bend, dy) in local coordinates
    num_points = 100
    t = np.linspace(0, 1, num_points)
    x_bend_local = t * L_bend_outer
    y_bend_local = (dy / 2.0) * (1 - np.cos(np.pi * t))
    
    # Offset bend to start at end of straight section
    x_bend = x_bend_local + L_straight_outer
    y_bend = y_bend_local 
    
    # Combine into one path array
    # Note: We omit the first point of the bend to avoid duplicating the join point
    points_x = np.concatenate([x_straight, x_bend[1:]])
    points_y = np.concatenate([y_straight, y_bend[1:]])
    points = np.column_stack((points_x, points_y))
    
    path_arm = gf.Path(points)
    
    # -- Width Transition --
    # The outer arm expands linearly from start to end over the full length
    xs_in = gf.cross_section.cross_section(width=w_outer_in, layer=(1, 0))
    xs_out = gf.cross_section.cross_section(width=w_outer_out, layer=(1, 0))
    
    transition = gf.path.transition(
        cross_section1=xs_in, 
        cross_section2=xs_out, 
        width_type="linear"
    )
    
    # Extrude the path with the width transition
    arm_comp = gf.path.extrude_transition(path_arm, transition)
    
    # --- 3. Placement ---
    
    # Top Arm
    top_ref = c << arm_comp
    top_ref.move((0, y_top_in))
    
    # Bottom Arm
    # Mirror across X axis and shift to negative Y position
    bot_ref = c << arm_comp
    bot_ref.mirror(p1=(0, 0), p2=(1, 0))
    bot_ref.move((0, -y_top_in))

    # --- 4. Ports ---
    c.add_port("o1", port=center.ports["o1"])
    # Manually adding output ports for the outer arms for completeness
    c.add_port("o2", center=(L_total, y_top_out), width=w_outer_out, orientation=0, layer=(1, 0))
    c.add_port("o3", center=(L_total, -y_top_out), width=w_outer_out, orientation=0, layer=(1, 0))

    return c

if __name__ == "__main__":
    device = trident_coupler()
    device.write_gds("trident_coupler.gds")