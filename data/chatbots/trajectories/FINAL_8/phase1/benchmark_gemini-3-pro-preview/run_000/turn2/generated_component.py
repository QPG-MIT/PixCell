import gdsfactory as gf

@gf.cell
def slotted_coupler_structure():
    """
    Recreation of the 5-waveguide slotted coupler.
    Consists of a central straight waveguide and two outer arms.
    Each outer arm has a thin inner rail and a thick outer rail.
    Footprint constraint: 120um x 4um.
    """
    c = gf.Component()

    # ---------------------------------------------------------
    # 1. Dimensions & Parameters
    # ---------------------------------------------------------
    total_length = 120.0
    coupling_length = 40.0  # Length of the parallel interaction region
    bend_length = (total_length - coupling_length) / 2
    
    # Widths based on visual estimation from target image
    w_thin = 0.25   # Width of center and inner rails
    w_thick = 0.65  # Width of outer rails
    
    # Gaps
    g_coupling = 0.2 # Gap between center WG and inner rail
    g_slot = 0.2     # Gap between inner rail and outer rail
    
    # Vertical S-bend shift (how far arms move away at input/output)
    # Must fit within 4um total height. 
    # Current Y max ~ 1.0um. bend_dy = 0.8 keeps us under +/- 2.0um.
    bend_dy = 0.8

    # ---------------------------------------------------------
    # 2. Define Cross Sections
    # ---------------------------------------------------------
    
    # -- Center Cross Section --
    xs_center = gf.cross_section.strip(width=w_thin, layer=(1, 0))

    # -- Top Arm Cross Section --
    # We define the path along the INNER (thin) rail.
    # The OUTER (thick) rail is attached as a section above it.
    offset_top_outer = (w_thin / 2) + g_slot + (w_thick / 2)
    
    s_top_outer = gf.Section(
        width=w_thick,
        offset=offset_top_outer, # Positive offset = Move UP (away from center)
        layer=(1, 0)
    )
    xs_top = gf.cross_section.cross_section(
        width=w_thin, # The main path draws the inner rail
        layer=(1, 0),
        sections=[s_top_outer]
    )

    # -- Bottom Arm Cross Section --
    # We define the path along the INNER (thin) rail.
    # The OUTER (thick) rail is attached as a section below it.
    offset_bot_outer = -((w_thin / 2) + g_slot + (w_thick / 2))
    
    s_bot_outer = gf.Section(
        width=w_thick,
        offset=offset_bot_outer, # Negative offset = Move DOWN (away from center)
        layer=(1, 0)
    )
    xs_bot = gf.cross_section.cross_section(
        width=w_thin, # The main path draws the inner rail
        layer=(1, 0),
        sections=[s_bot_outer]
    )

    # ---------------------------------------------------------
    # 3. Component Assembly
    # ---------------------------------------------------------

    # --- A. Center Waveguide (Runs straight through) ---
    wg_center = c << gf.components.straight(
        length=total_length, 
        cross_section=xs_center
    )
    # wg_center starts at (0,0) by default

    # --- B. Top Arm Assembly ---
    # Calculate Y position in the coupling region (Center of inner rail)
    # Center WG is at y=0, edge at w_thin/2.
    # Inner rail edge starts at w_thin/2 + g_coupling.
    # Inner rail center is at w_thin/2 + g_coupling + w_thin/2
    y_top_coupling = w_thin + g_coupling

    # 1. Input S-Bend (Left)
    # Starts high, goes down to coupling Y
    t_bend_in = c << gf.components.bend_s(
        size=(bend_length, -bend_dy), # Negative Y = bending down
        cross_section=xs_top
    )
    # Anchor the end of the bend (o2) to the start of the straight section
    # We want the end of the bend to be at x=bend_length, y=y_top_coupling
    t_bend_in.move(origin=t_bend_in.ports["o2"].center, destination=(bend_length, y_top_coupling))

    # 2. Straight Coupling Section
    t_straight = c << gf.components.straight(
        length=coupling_length, 
        cross_section=xs_top
    )
    t_straight.connect("o1", t_bend_in.ports["o2"])

    # 3. Output S-Bend (Right)
    # Starts at coupling Y, goes up
    t_bend_out = c << gf.components.bend_s(
        size=(bend_length, bend_dy), # Positive Y = bending up
        cross_section=xs_top
    )
    t_bend_out.connect("o1", t_straight.ports["o2"])

    # --- C. Bottom Arm Assembly ---
    y_bot_coupling = -y_top_coupling

    # 1. Input S-Bend (Left)
    # Starts low, goes up to coupling Y
    b_bend_in = c << gf.components.bend_s(
        size=(bend_length, bend_dy), # Positive Y = bending up
        cross_section=xs_bot
    )
    # Anchor end (o2) to (bend_length, y_bot_coupling)
    b_bend_in.move(origin=b_bend_in.ports["o2"].center, destination=(bend_length, y_bot_coupling))

    # 2. Straight Coupling Section
    b_straight = c << gf.components.straight(
        length=coupling_length, 
        cross_section=xs_bot
    )
    b_straight.connect("o1", b_bend_in.ports["o2"])

    # 3. Output S-Bend (Right)
    # Starts at coupling Y, goes down
    b_bend_out = c << gf.components.bend_s(
        size=(bend_length, -bend_dy), # Negative Y = bending down
        cross_section=xs_bot
    )
    b_bend_out.connect("o1", b_straight.ports["o2"])

    return c

if __name__ == "__main__":
    # Create and display the device
    device = slotted_coupler_structure()
    device.show()
    device.write_gds("slotted_coupler_corrected.gds")