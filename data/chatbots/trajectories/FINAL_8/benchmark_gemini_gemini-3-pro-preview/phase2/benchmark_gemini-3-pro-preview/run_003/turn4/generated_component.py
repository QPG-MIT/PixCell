import gdsfactory as gf

@gf.cell
def device_recreation_final():
    """
    Final recreation of the waveguide array matching target visual characteristics
    and geometric constraints.
    Features:
    - 4.0um vertical constraint compliance.
    - Central bundle: 5 fine lines.
    - Outer bundles: 4 'thick' lines appearing as blocks with slits.
    - Distinct 'straight-flare-straight' profile implemented via central straight + S-bend flares.
    """
    c = gf.Component()
    
    # ---------------------------
    # 1. Dimensions
    # ---------------------------
    L_total = 120.0
    L_mid = 40.0
    L_bend = (L_total - L_mid) / 2.0  # 40.0
    
    # Vertical parameters optimized for 4.0um height limit
    # While maximizing the visible flare to match the target image.
    
    # Central Bundle: 5 fine lines (Striped texture)
    w_center = 0.08
    gap_center = 0.08
    p_center = w_center + gap_center
    n_center = 5
    xs_center = gf.cross_section.strip(width=w_center)
    
    # Outer Bundles: 4 thick lines (Solid block texture with slits)
    # Using high width/gap ratio to simulate the solid block look
    w_outer = 0.20
    gap_outer = 0.04
    p_outer = w_outer + gap_outer
    n_outer = 4
    xs_outer = gf.cross_section.strip(width=w_outer)
    
    # Spacing
    gap_waist = 0.12  # Gap between center bundle and outer bundles at the narrowest point
    
    # Flare Height (dy)
    # Calculation of stack height at waist:
    # Center height approx: 4*0.16 + 0.08 = 0.72
    # Waist gaps: 2 * 0.12 = 0.24
    # Outer bundles height: 2 * (3*0.24 + 0.20) = 2 * 0.92 = 1.84
    # Total Waist Height = 2.80 um
    # Max allowed height = 4.0 um
    # Max flare total = 1.2 um => 0.6 um per side.
    dy_flare = 0.6

    # ---------------------------
    # 2. Build Central Bundle
    # ---------------------------
    # Centered around y=0, x=0
    # Length = L_total (Straight through)
    y_c_start = -((n_center - 1) * p_center) / 2
    for i in range(n_center):
        y = y_c_start + i * p_center
        wg = c << gf.components.straight(length=L_total, cross_section=xs_center)
        wg.x = 0
        wg.y = y

    # ---------------------------
    # 3. Build Top Outer Bundle
    # ---------------------------
    # Starting y for the lowest waveguide in the top bundle (at the waist)
    y_center_max = y_c_start + (n_center - 1) * p_center + w_center/2
    y_top_first_center = y_center_max + gap_waist + w_outer/2
    
    for i in range(n_outer):
        # Y position in the straight middle section
        y_mid = y_top_first_center + i * p_outer
        
        # A. Middle Straight Section
        wg_mid = c << gf.components.straight(length=L_mid, cross_section=xs_outer)
        wg_mid.x = 0
        wg_mid.y = y_mid
        
        # B. Right S-Bend (Flare UP and RIGHT)
        # Connects to East port ("o2"), moves +x, bends +y
        sb_r = c << gf.components.bend_s(size=(L_bend, dy_flare), cross_section=xs_outer)
        sb_r.connect("o1", wg_mid.ports["o2"])
        
        # C. Left S-Bend (Flare UP and LEFT)
        # Connects to West port ("o1"), moves -x.
        # To bend Global UP (+y) while moving Global LEFT (-x) in a rotated 180 frame,
        # we need a Local DOWN bend (-y).
        sb_l = c << gf.components.bend_s(size=(L_bend, -dy_flare), cross_section=xs_outer)
        sb_l.connect("o1", wg_mid.ports["o1"])

    # ---------------------------
    # 4. Build Bottom Outer Bundle
    # ---------------------------
    # Mirror logic
    for i in range(n_outer):
        # Y position in the straight middle section (negative)
        y_mid = -(y_top_first_center + i * p_outer)
        
        # A. Middle Straight Section
        wg_mid = c << gf.components.straight(length=L_mid, cross_section=xs_outer)
        wg_mid.x = 0
        wg_mid.y = y_mid
        
        # B. Right S-Bend (Flare DOWN and RIGHT)
        # Connects to East port, bends -y
        sb_r = c << gf.components.bend_s(size=(L_bend, -dy_flare), cross_section=xs_outer)
        sb_r.connect("o1", wg_mid.ports["o2"])
        
        # C. Left S-Bend (Flare DOWN and LEFT)
        # Connects to West port.
        # To bend Global DOWN (-y) while moving Global LEFT (-x) in rotated 180 frame,
        # we need a Local UP bend (+y).
        sb_l = c << gf.components.bend_s(size=(L_bend, dy_flare), cross_section=xs_outer)
        sb_l.connect("o1", wg_mid.ports["o1"])

    return c

# Create and save
device = device_recreation_final()
device.write_gds("device_recreation_final.gds")