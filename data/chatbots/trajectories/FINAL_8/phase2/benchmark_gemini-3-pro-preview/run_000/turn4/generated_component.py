import gdsfactory as gf
from gdsfactory.cross_section import Section

@gf.cell
def specialized_coupler_refined():
    """
    Refined parametric coupler based on visual feedback.
    Adjusted gaps and widths to ensure clear separation of rails 
    and matching the 'candy wrapper' aesthetic.
    """
    c = gf.Component()

    # =======================================================================
    # 1. Dimensions & Constraints
    # =======================================================================
    # Geometric Constraints
    L_total = 120.0
    L_straight = 50.0  # Elongated straight section to match aspect ratio
    L_bend = (L_total - L_straight) / 2 # 35.0

    # Feature Sizes (Adjusted for visual clarity)
    w_thin = 0.15      # Width of the thin rails (approx 150nm)
    w_thick = 0.5      # Width of the outer slab (reduced from 0.6 for elegance)
    gap = 0.2          # Gap between waveguides (increased for visual separation)

    # Vertical Offsets
    # Central Rail is at y=0
    
    # Arm Geometry (Top)
    # The 'Path' for the top arm is the center of the innermost rail.
    # Relative to the center rail (y=0):
    # Center_Rail_Top_Edge = w_thin/2
    # Inner_Rail_Bot_Edge = Center_Rail_Top_Edge + gap
    # Inner_Rail_Center = Inner_Rail_Bot_Edge + w_thin/2
    y_arm_core = (w_thin / 2) + gap + (w_thin / 2) # 0.075 + 0.2 + 0.075 = 0.35

    # Offsets within the Arm (Relative to Inner Rail Center)
    # Rail 2 Center:
    # Gap between Rail 1 and Rail 2 is 'gap'
    off_rail2 = (w_thin / 2) + gap + (w_thin / 2) # 0.35

    # Block Center:
    # Gap between Rail 2 and Block is 'gap'
    off_block = off_rail2 + (w_thin / 2) + gap + (w_thick / 2)
    # 0.35 + 0.075 + 0.2 + 0.25 = 0.875

    # S-Bend Flare height (vertical displacement)
    dy_flare = 1.0  # Vertical drop for the S-bends

    # =======================================================================
    # 2. Parametric Cross-Sections
    # =======================================================================

    # --- Center Rail ---
    xs_center = gf.cross_section.cross_section(
        width=w_thin,
        layer=(1, 0)
    )

    # --- Top Arm ---
    # Path = Inner Rail
    # Sections added to positive offset (Up/Left)
    sections_top = [
        Section(width=w_thin, offset=off_rail2, layer=(1, 0)),
        Section(width=w_thick, offset=off_block, layer=(1, 0))
    ]
    xs_top = gf.cross_section.cross_section(
        width=w_thin,
        sections=sections_top,
        layer=(1, 0)
    )

    # --- Bottom Arm ---
    # Path = Inner Rail
    # Sections added to negative offset (Down/Right)
    sections_bot = [
        Section(width=w_thin, offset=-off_rail2, layer=(1, 0)),
        Section(width=w_thick, offset=-off_block, layer=(1, 0))
    ]
    xs_bot = gf.cross_section.cross_section(
        width=w_thin,
        sections=sections_bot,
        layer=(1, 0)
    )

    # =======================================================================
    # 3. Geometry Construction
    # =======================================================================

    # 1. Central Stationary Rail
    center = c << gf.components.straight(length=L_straight, cross_section=xs_center)
    center.move((L_bend, 0))

    # 2. Top Arm Construction
    #   A. Straight Coupling Region
    top_straight = c << gf.components.straight(length=L_straight, cross_section=xs_top)
    top_straight.move((L_bend, y_arm_core))

    #   B. Input S-Bend (Left)
    #   Curves from (High Y) down to (Coupling Y).
    top_bend_in = c << gf.components.bend_s(
        size=(L_bend, -dy_flare), 
        cross_section=xs_top
    )
    # Connect output of bend to input of straight
    top_bend_in.connect("o2", top_straight.ports["o1"])

    #   C. Output S-Bend (Right)
    #   Curves from (Coupling Y) up to (High Y).
    top_bend_out = c << gf.components.bend_s(
        size=(L_bend, dy_flare), 
        cross_section=xs_top
    )
    top_bend_out.connect("o1", top_straight.ports["o2"])

    # 3. Bottom Arm Construction
    #   A. Straight Coupling Region
    bot_straight = c << gf.components.straight(length=L_straight, cross_section=xs_bot)
    bot_straight.move((L_bend, -y_arm_core))

    #   B. Input S-Bend (Left)
    #   Curves from (Low Y) up to (Coupling Y).
    bot_bend_in = c << gf.components.bend_s(
        size=(L_bend, dy_flare), 
        cross_section=xs_bot
    )
    bot_bend_in.connect("o2", bot_straight.ports["o1"])

    #   C. Output S-Bend (Right)
    #   Curves from (Coupling Y) down to (Low Y).
    bot_bend_out = c << gf.components.bend_s(
        size=(L_bend, -dy_flare), 
        cross_section=xs_bot
    )
    bot_bend_out.connect("o1", bot_straight.ports["o2"])

    return c

if __name__ == "__main__":
    component = specialized_coupler_refined()
    component.show()
    component.write_gds("specialized_coupler_refined.gds")