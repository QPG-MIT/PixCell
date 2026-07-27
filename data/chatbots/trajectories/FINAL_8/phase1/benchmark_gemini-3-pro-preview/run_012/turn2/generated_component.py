import gdsfactory as gf
from gdsfactory.cross_section import Section

@gf.cell
def specialized_coupler_fixed():
    """
    Corrected generation of the multi-rail directional coupler.
    Uses explicit trajectory construction (Left->Right) with negative Y-offsets
    to ensure cross-section orientation (thick blocks on outside) is preserved.
    """
    c = gf.Component()

    # =======================================================================
    # 1. Dimensions & Parameters
    # =======================================================================
    # Lengths
    L_bend = 40.0
    L_straight = 40.0
    
    # Widths and Gaps
    # Adjusted to match visual proportions of the original image
    w_thin = 0.15          # Very thin inner rails
    w_thick = 1.0          # Robust outer blocks
    gap_coupling = 0.2     # Gap between center rail and arm
    gap_intra = 0.2        # Gap between parallel rails within an arm
    
    # Vertical Offsets for Cross Section Definition
    # We define the path as the center of the innermost rail (Rail 1).
    # Rail 2 is offset relative to Rail 1:
    pitch_rails = w_thin + gap_intra
    
    # Thick Block offset relative to Rail 1:
    # Rail 1 Center -> Rail 2 Center -> Block Center
    offset_block = pitch_rails + (w_thin/2) + gap_intra + (w_thick/2)
    
    # Vertical Geometry (World Coordinates)
    # y=0 is the center of the central rail.
    half_center = w_thin / 2
    
    # The innermost rail of the arm sits at:
    y_coupling_center_top = half_center + gap_coupling + (w_thin/2)
    y_coupling_center_bot = -y_coupling_center_top
    
    # Flare height: How much the S-bends drop/rise from input to coupling region
    dy_flare = 1.2

    # =======================================================================
    # 2. Define Parametric Cross-Sections
    # =======================================================================
    
    # -- Center Rail XS --
    xs_center = gf.cross_section.cross_section(
        width=w_thin,
        layer=(1, 0)
    )

    # -- Top Arm XS --
    # Path is the inner rail. Positive offset is "Left" (Top).
    # We add Rail 2 and Block to the "Left".
    s_top = [
        Section(width=w_thin, offset=pitch_rails, layer=(1, 0)),
        Section(width=w_thick, offset=offset_block, layer=(1, 0))
    ]
    xs_top = gf.cross_section.cross_section(
        width=w_thin,     # Main core (Rail 1)
        sections=s_top,
        layer=(1, 0)
    )

    # -- Bottom Arm XS --
    # Path is the inner rail. Negative offset is "Right" (Bottom).
    # We add Rail 2 and Block to the "Right".
    s_bot = [
        Section(width=w_thin, offset=-pitch_rails, layer=(1, 0)),
        Section(width=w_thick, offset=-offset_block, layer=(1, 0))
    ]
    xs_bot = gf.cross_section.cross_section(
        width=w_thin,
        sections=s_bot,
        layer=(1, 0)
    )

    # =======================================================================
    # 3. Component Construction (Left -> Right)
    # =======================================================================
    
    # --- Center Straight Rail ---
    center_rail = c << gf.components.straight(
        length=L_straight,
        cross_section=xs_center
    )
    center_rail.move((L_bend, 0)) # Centered longitudinally
    
    # --- Top Arm ---
    # 1. Input S-Bend (Drops DOWN from High Y to Coupling Y)
    # Start Y: y_coupling + dy_flare
    # End Y: y_coupling
    # Delta Y: -dy_flare
    bend_top_in = c << gf.components.bend_s(
        size=(L_bend, -dy_flare),
        cross_section=xs_top
    )
    # Move start to correct input position
    bend_top_in.move((0, y_coupling_center_top + dy_flare))
    
    # 2. Straight Coupling Section
    straight_top = c << gf.components.straight(
        length=L_straight,
        cross_section=xs_top
    )
    straight_top.connect("o1", bend_top_in.ports["o2"])
    
    # 3. Output S-Bend (Goes UP from Coupling Y to High Y)
    # Delta Y: +dy_flare
    bend_top_out = c << gf.components.bend_s(
        size=(L_bend, dy_flare),
        cross_section=xs_top
    )
    bend_top_out.connect("o1", straight_top.ports["o2"])

    # --- Bottom Arm ---
    # 1. Input S-Bend (Goes UP from Low Y to Coupling Y)
    # Start Y: y_coupling_bot - dy_flare
    # End Y: y_coupling_bot
    # Delta Y: +dy_flare
    bend_bot_in = c << gf.components.bend_s(
        size=(L_bend, dy_flare),
        cross_section=xs_bot
    )
    bend_bot_in.move((0, y_coupling_center_bot - dy_flare))
    
    # 2. Straight Coupling Section
    straight_bot = c << gf.components.straight(
        length=L_straight,
        cross_section=xs_bot
    )
    straight_bot.connect("o1", bend_bot_in.ports["o2"])
    
    # 3. Output S-Bend (Goes DOWN from Coupling Y to Low Y)
    # Delta Y: -dy_flare
    bend_bot_out = c << gf.components.bend_s(
        size=(L_bend, -dy_flare),
        cross_section=xs_bot
    )
    bend_bot_out.connect("o1", straight_bot.ports["o2"])

    return c

if __name__ == "__main__":
    component = specialized_coupler_fixed()
    component.show()
    component.write_gds("specialized_coupler_fixed.gds")