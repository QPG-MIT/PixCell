import gdsfactory as gf

@gf.cell
def dense_coupler_bundle():
    """
    Creates a dense multi-waveguide coupler with a straight central bundle
    and flared outer bundles.
    
    Replaces built-in array functions with manual loops to ensure compatibility
    across different GDSFactory/KFactory versions.
    """
    c = gf.Component()

    # --- 1. Parameters & Constraints ---
    # Footprint constraint: 120um x 4um
    length_total = 120.0
    
    # Waveguide dimensions
    wg_width = 0.15       
    gap = 0.1             # Tight gap for high density
    pitch = wg_width + gap
    
    # Counts
    n_center = 5
    n_outer = 4
    
    # Longitudinal dimensions
    length_bend = 15.0
    length_straight = length_total - 2 * length_bend
    
    # Vertical flare (how much outer bundles move away at the ends)
    flare_height = 0.4

    # Cross-section
    xs_poly = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 2. Define Sub-Components ---

    # A. Straight Waveguide (for center bundle)
    # Origin at (0,0), runs along X
    wg_center = gf.components.straight(length=length_total, cross_section=xs_poly)

    # B. Top Rail Component
    # Designed relative to the Straight Interaction Region being at y=0
    # Shape: High (Input) -> Down -> Straight -> Up -> High (Output)
    c_top = gf.Component("top_rail")
    
    # 1. Straight Section (Interaction Zone)
    # Place it centered in X relative to the total length
    # Total length is 120. Bends are 15. Straight is 90.
    # We place the straight section starting at x = length_bend
    st_top = c_top << gf.components.straight(length=length_straight, cross_section=xs_poly)
    st_top.movex(length_bend)
    
    # 2. Input S-Bend (Left)
    # Starts at x=0, y=flare_height. Ends at x=length_bend, y=0.
    sbend_geom = gf.components.bend_s(
        size=(length_bend, flare_height), 
        cross_section=xs_poly
    )
    # bend_s usually goes Low->High. We need High->Low.
    s_in_top = c_top << sbend_geom
    s_in_top.mirror_y() # Now goes High->Low
    s_in_top.movey(flare_height) # Shift up so input is at y=flare_height, output at y=0
    
    # 3. Output S-Bend (Right)
    # Starts at x=length_bend+length_straight, y=0. Ends at total_length, y=flare_height.
    s_out_top = c_top << sbend_geom
    s_out_top.movex(length_bend + length_straight)
    
    # C. Bottom Rail Component
    # Mirror of Top Rail: Low (Input) -> Up -> Straight -> Down -> Low (Output)
    c_bot = gf.Component("bot_rail")
    
    # 1. Straight Section
    st_bot = c_bot << gf.components.straight(length=length_straight, cross_section=xs_poly)
    st_bot.movex(length_bend)
    
    # 2. Input S-Bend (Left)
    # Needs to go Low->High (standard bend_s behavior).
    # Starts at x=0, y=-flare_height. Ends at x=length_bend, y=0.
    s_in_bot = c_bot << sbend_geom
    s_in_bot.movey(-flare_height)
    
    # 3. Output S-Bend (Right)
    # Needs to go High->Low (mirrored).
    # Starts at end of straight (y=0) -> goes down to -flare_height
    s_out_bot = c_bot << sbend_geom
    s_out_bot.mirror_y()
    s_out_bot.movex(length_bend + length_straight)
    # No Y-shift needed after mirror because mirror flips around y=0 (input at 0, output at -height)

    # --- 3. Assembly (Manual Loop Placement) ---

    # A. Place Center Bundle
    # Centered around Y=0
    center_y_start = -((n_center - 1) * pitch) / 2
    for i in range(n_center):
        ref = c << wg_center
        ref.movey(center_y_start + i * pitch)

    # B. Place Top Bundle
    # The straight section of the first top rail should be `pitch` above the top center rail.
    # Top center rail is at: center_y_start + (n_center-1)*pitch = +center_height/2
    y_top_start = (center_y_start + (n_center - 1) * pitch) + pitch
    
    for i in range(n_outer):
        ref = c << c_top
        # The c_top component has its straight section at y=0 local.
        # So we just move it to the target Y.
        ref.movey(y_top_start + i * pitch)

    # C. Place Bottom Bundle
    # The straight section of the first bottom rail should be `pitch` below the bottom center rail.
    # Bottom center rail is at: center_y_start
    y_bot_start = center_y_start - pitch
    
    for i in range(n_outer):
        ref = c << c_bot
        # We place them downwards.
        # y_bot_start is the "highest" of the bottom bundle (closest to center).
        # subsequent rails go down.
        ref.movey(y_bot_start - i * pitch)

    return c

if __name__ == "__main__":
    device = dense_coupler_bundle()
    device.show()
    device.write_gds("dense_coupler_corrected.gds")