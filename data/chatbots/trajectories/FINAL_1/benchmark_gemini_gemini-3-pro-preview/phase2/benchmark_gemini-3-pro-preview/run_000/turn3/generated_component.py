import gdsfactory as gf
import numpy as np

@gf.cell
def device_inverse_taper():
    c = gf.Component()

    # --- Dimensions & Constraints ---
    # Global device footprint constraints
    length_total = 40.0
    height_footprint = 1.7
    
    # Longitudinal segmentation lengths
    # Based on the target image: 
    # 1. A long straight input section where side arms are parallel.
    # 2. A transition zone (knee) where side arms flare out and widen.
    # 3. A final straight output section.
    l_in_straight = 18.0
    l_transition = 14.0
    l_out_straight = 8.0  # (18 + 14 + 8 = 40.0)
    
    # Central taper length
    # The central taper should terminate partially into the transition zone to 
    # ensure adiabatic mode handover to the side arms.
    l_taper = 25.0 

    # Transverse dimensions (Widths)
    w_center_start = 0.35   # Central core width
    w_center_end = 0.03     # Taper tip width
    
    w_side_start = 0.15     # Narrow input for side arms
    w_side_end = 0.55       # Wide output for side arms (creating the large black blocks on the right)
    
    gap_in = 0.1            # Coupling gap at input
    
    layer_wg = (1, 0)

    # --- Geometry Calculations ---
    
    # 1. Y-positions at input
    # Center waveguide is at y=0. Side waveguides are symmetric.
    y_side_in_abs = (w_center_start / 2.0) + gap_in + (w_side_start / 2.0)
    
    # 2. Y-positions at output
    # Outer boundaries are fixed by the footprint height.
    # Top edge = 1.7 / 2 = 0.85
    # Center of top arm = 0.85 - (width/2)
    y_side_out_abs = (height_footprint / 2.0) - (w_side_end / 2.0)
    
    # Vertical shift (Dy) required for the S-bend
    dy = y_side_out_abs - y_side_in_abs
    
    # --- Components Construction ---

    # 1. Central Taper
    taper = c << gf.components.taper(
        length=l_taper,
        width1=w_center_start,
        width2=w_center_end,
        layer=layer_wg
    )
    taper.move((0, 0))

    # Define Cross Sections for Input and Output of side arms
    xs_side_in = gf.cross_section.cross_section(width=w_side_start, layer=layer_wg)
    xs_side_out = gf.cross_section.cross_section(width=w_side_end, layer=layer_wg)

    # --- Top Arm Construction ---
    
    # Segment 1: Straight Input
    top_s1 = c << gf.components.straight(length=l_in_straight, cross_section=xs_side_in)
    top_s1.move((0, y_side_in_abs))
    
    # Segment 2: S-Bend with Width Transition
    # We generate a path for a cosine-shaped S-bend.
    t = np.linspace(0, 1, 101)
    x_pts = l_transition * t
    y_pts = dy * (1 - np.cos(np.pi * t)) / 2.0 
    
    pts_top = np.column_stack((x_pts, y_pts))
    path_top = gf.Path(pts_top)
    
    # Create width transition (sine profile handles the width expansion smoothly)
    transition = gf.path.transition(xs_side_in, xs_side_out, width_type='sine')
    
    top_s2 = c << gf.path.extrude_transition(path_top, transition)
    top_s2.connect("o1", top_s1.ports["o2"])
    
    # Segment 3: Straight Output
    top_s3 = c << gf.components.straight(length=l_out_straight, cross_section=xs_side_out)
    top_s3.connect("o1", top_s2.ports["o2"])
    
    # --- Bottom Arm Construction (Symmetric) ---
    
    # Segment 1: Straight Input
    bot_s1 = c << gf.components.straight(length=l_in_straight, cross_section=xs_side_in)
    bot_s1.move((0, -y_side_in_abs))
    
    # Segment 2: S-Bend (Negative Dy for downward bend)
    y_pts_bot = -dy * (1 - np.cos(np.pi * t)) / 2.0
    pts_bot = np.column_stack((x_pts, y_pts_bot))
    path_bot = gf.Path(pts_bot)
    
    bot_s2 = c << gf.path.extrude_transition(path_bot, transition)
    bot_s2.connect("o1", bot_s1.ports["o2"])
    
    # Segment 3: Straight Output
    bot_s3 = c << gf.components.straight(length=l_out_straight, cross_section=xs_side_out)
    bot_s3.connect("o1", bot_s2.ports["o2"])

    # Flatten to merge cells and fix any off-grid vertex issues
    c.flatten()
    return c

# Generate and save
device = device_inverse_taper()
device.write_gds("inverse_taper_coupler.gds")