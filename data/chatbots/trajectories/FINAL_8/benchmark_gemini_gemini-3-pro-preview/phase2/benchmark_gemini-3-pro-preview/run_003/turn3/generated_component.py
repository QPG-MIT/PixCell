import gdsfactory as gf

@gf.cell
def device_recreation_refined_v2():
    """
    Refined recreation of the waveguide array.
    - Matches the "thick block" appearance of outer bundles using wide waveguides with narrow gaps.
    - Matches the 5-line fine structure of the central bundle.
    - Implements the 'straight-flare-straight' logic correctly within the 4um height constraint.
    """
    c = gf.Component()
    
    # ---------------------------
    # 1. Dimensions
    # ---------------------------
    L_total = 120.0
    L_mid = 40.0
    L_bend = (L_total - L_mid) / 2.0 # 40.0
    
    # Flare height (vertical displacement of the S-bends at the ends)
    dy_flare = 0.2 
    
    # ---------------------------
    # 2. Cross Sections
    # ---------------------------
    # Central Bundle: 5 fine lines
    w_center = 0.12
    gap_center = 0.1
    p_center = w_center + gap_center
    xs_center = gf.cross_section.strip(width=w_center)
    n_center = 5
    
    # Outer Bundles: 4 thick lines (appearing as blocks with slits)
    w_outer = 0.25
    gap_outer = 0.05
    p_outer = w_outer + gap_outer
    xs_outer = gf.cross_section.strip(width=w_outer)
    n_outer = 4
    
    # ---------------------------
    # 3. Build Central Bundle
    # ---------------------------
    # Centered around y=0
    for i in range(n_center):
        y_pos = (i - (n_center - 1) / 2) * p_center
        wg = c << gf.components.straight(length=L_total, cross_section=xs_center)
        wg.x = 0
        wg.y = y_pos

    # ---------------------------
    # 4. Build Top Outer Bundle
    # ---------------------------
    # Calculate starting Y position for the straight middle section.
    # We pack it close to the center to allow room to flare out.
    
    y_center_max = ((n_center - 1) * p_center) / 2 + w_center/2
    gap_mid_spacing = 0.15 # Gap between central bundle and outer bundle in the middle
    
    # y position of the first (bottom-most) line of the top bundle
    y_top_start = y_center_max + gap_mid_spacing + w_outer/2
    
    for i in range(n_outer):
        # Y position in the straight middle section
        y_mid = y_top_start + i * p_outer
        
        # A. Middle Straight Section
        wg_mid = c << gf.components.straight(length=L_mid, cross_section=xs_outer)
        wg_mid.x = 0
        wg_mid.y = y_mid
        
        # B. Right S-Bend (Flare UP and RIGHT)
        # Moves from (x_end, y_mid) to (x_end + L_bend, y_mid + dy)
        sb_r = c << gf.components.bend_s(size=(L_bend, dy_flare), cross_section=xs_outer)
        sb_r.connect("o1", wg_mid.ports["o2"])
        
        # C. Left S-Bend (Flare UP and LEFT)
        # Connecting to "o1" (West port) means we are moving in -x direction.
        # To move UP in global coordinates while moving Left, we need a local "down" bend 
        # because the port frame is rotated 180 degrees.
        # Local (L, -dy) rotated 180 -> Global (-L, -(-dy)) = (-L, +dy)
        sb_l = c << gf.components.bend_s(size=(L_bend, -dy_flare), cross_section=xs_outer)
        sb_l.connect("o1", wg_mid.ports["o1"])

    # ---------------------------
    # 5. Build Bottom Outer Bundle
    # ---------------------------
    # Mirror logic for bottom
    y_bot_start = -y_top_start
    
    for i in range(n_outer):
        # Y position in the straight middle section (going downwards)
        y_mid = y_bot_start - i * p_outer
        
        # A. Middle Straight Section
        wg_mid = c << gf.components.straight(length=L_mid, cross_section=xs_outer)
        wg_mid.x = 0
        wg_mid.y = y_mid
        
        # B. Right S-Bend (Flare DOWN and RIGHT)
        # Moves y down by dy_flare
        sb_r = c << gf.components.bend_s(size=(L_bend, -dy_flare), cross_section=xs_outer)
        sb_r.connect("o1", wg_mid.ports["o2"])
        
        # C. Left S-Bend (Flare DOWN and LEFT)
        # Local (L, dy) rotated 180 -> Global (-L, -dy)
        sb_l = c << gf.components.bend_s(size=(L_bend, dy_flare), cross_section=xs_outer)
        sb_l.connect("o1", wg_mid.ports["o1"])

    return c

# Create and save
device = device_recreation_refined_v2()
device.write_gds("device_recreation_refined_v2.gds")