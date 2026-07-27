import gdsfactory as gf

@gf.cell
def dense_coupler_bundle():
    """
    Creates a dense multi-waveguide coupler with a straight central bundle
    and flared outer bundles, matching the visual style of the reference.
    
    Key Features:
    - Central bundle of 5 straight waveguides
    - Outer bundles of 4 waveguides each, flaring out at ports
    - Smooth S-bends occupying significant length (35um) to match visual flow
    - Strict adherence to 120x4um footprint
    """
    c = gf.Component()

    # --- 1. Geometric Parameters ---
    length_total = 120.0
    
    # Increased bend length to match the gentle, sweeping curve of the original image
    length_bend = 35.0
    length_straight = length_total - 2 * length_bend
    
    # Waveguide Configuration
    # Slightly thicker lines (0.16) for better visual weight matching the original
    wg_width = 0.16       
    gap = 0.1             
    pitch = wg_width + gap
    
    n_center = 5
    n_outer = 4
    
    # Flare Height Calculation
    # Total height occupied by 13 waveguides + 12 gaps = 13*0.16 + 1.2 = 3.28um
    # Available budget = 4.0 - 3.28 = 0.72um
    # Flare per side = 0.36um. We use 0.35um to ensure it stays within bounds.
    flare_height = 0.35

    # Cross-section definition
    xs_poly = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 2. Component Definitions ---

    # A. Straight Waveguide (Center Bundle)
    # Simple straight line running the full length
    wg_center = gf.components.straight(length=length_total, cross_section=xs_poly)

    # B. Top Rail (Top Bundle Element)
    # Shape: High (Input) -> S-Bend-Down -> Straight -> S-Bend-Up -> High (Output)
    rail_top = gf.Component("rail_top")
    
    # Straight section (Interaction Zone) - centered in X
    st_top = rail_top << gf.components.straight(length=length_straight, cross_section=xs_poly)
    st_top.movex(length_bend)
    
    # Geometry for the S-Bend
    sbend_geom = gf.components.bend_s(
        size=(length_bend, flare_height), 
        cross_section=xs_poly
    )
    
    # Input S-Bend: Starts High, goes Down to Straight (y=0)
    # We mirror the standard Up-bend to make it a Down-bend
    s_in_top = rail_top << sbend_geom
    s_in_top.mirror_y() 
    s_in_top.movey(flare_height) 
    
    # Output S-Bend: Starts Straight (y=0), goes Up to High
    s_out_top = rail_top << sbend_geom
    s_out_top.movex(length_bend + length_straight)
    
    # C. Bottom Rail (Bottom Bundle Element)
    # Shape: Low (Input) -> S-Bend-Up -> Straight -> S-Bend-Down -> Low (Output)
    rail_bot = gf.Component("rail_bot")
    
    # Straight section
    st_bot = rail_bot << gf.components.straight(length=length_straight, cross_section=xs_poly)
    st_bot.movex(length_bend)
    
    # Input S-Bend: Starts Low, goes Up to Straight (y=0)
    # Standard S-bend goes Low->High, so we just shift it down
    s_in_bot = rail_bot << sbend_geom
    s_in_bot.movey(-flare_height)
    
    # Output S-Bend: Starts Straight (y=0), goes Down to Low
    s_out_bot = rail_bot << sbend_geom
    s_out_bot.mirror_y()
    s_out_bot.movex(length_bend + length_straight)

    # --- 3. Assembly ---

    # Calculate Vertical Offsets
    # The center bundle spans from roughly -2*pitch to +2*pitch
    center_y_top_wg = ((n_center - 1) / 2) * pitch
    
    # A. Place Center Bundle (5 lines)
    for i in range(n_center):
        ref = c << wg_center
        # Center the bundle around y=0
        y_pos = -center_y_top_wg + (i * pitch)
        ref.movey(y_pos)

    # B. Place Top Bundle (4 lines)
    # The straight section of the first top rail is placed `pitch` above the top center rail.
    # This ensures uniform gap spacing in the interaction region.
    y_top_start = center_y_top_wg + pitch
    
    for i in range(n_outer):
        ref = c << rail_top
        ref.movey(y_top_start + (i * pitch))

    # C. Place Bottom Bundle (4 lines)
    # Mirrored placement downwards
    y_bot_start = -center_y_top_wg - pitch
    
    for i in range(n_outer):
        ref = c << rail_bot
        # Build downwards: index 0 is closest to center
        ref.movey(y_bot_start - (i * pitch))

    return c

if __name__ == "__main__":
    device = dense_coupler_bundle()
    device.show()
    device.write_gds("dense_coupler_corrected.gds")