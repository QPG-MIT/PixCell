import gdsfactory as gf

@gf.cell
def tapered_multi_coupler_v2():
    c = gf.Component()

    # --- Dimensions & Constraints ---
    # Footprint: 120um x 4um
    L_total = 120.0
    H_total = 4.0
    
    # Feature sizes tuned for visual match
    # Inner waveguides are fine lines, Outer waveguides are thick blocks
    w_inner = 0.15
    w_outer = 1.25  
    gap = 0.12      
    
    # Length distribution
    # Long straight interaction section, short flaring bends
    L_straight = 96.0
    L_bend = (L_total - L_straight) / 2  # 12.0 um

    # --- Vertical Layout (Y-axis) ---
    # Centered at y=0. 
    # Stack: Outer(Top) - gap - Inner(Top) - gap - Inner(Mid) - gap - Inner(Bot) - gap - Outer(Bot)
    
    # 1. Inner Waveguide Positions
    # Center WG at y=0
    # Pitch (center-to-center distance)
    pitch_inner = w_inner + gap
    y_inner_top = pitch_inner
    y_inner_mid = 0
    y_inner_bot = -pitch_inner

    # 2. Outer Waveguide Positions (Straight Section)
    # Calculate offset to maintain constant 'gap'
    # Distance = (Half Inner Width) + Gap + (Half Outer Width)
    offset_outer = (w_inner / 2) + gap + (w_outer / 2)
    y_outer_top_s = y_inner_top + offset_outer
    y_outer_bot_s = -y_outer_top_s

    # 3. Bend Offset (dy) Calculation
    # We want the outer edge of the port to align exactly with the footprint limit (+/- 2.0um)
    current_top_edge = y_outer_top_s + (w_outer / 2)
    target_top_edge = H_total / 2
    dy = target_top_edge - current_top_edge
    
    # --- Cross Sections ---
    xs_inner = gf.cross_section.cross_section(width=w_inner, layer=(1, 0))
    xs_outer = gf.cross_section.cross_section(width=w_outer, layer=(1, 0))

    # --- Geometry Generation ---

    # 1. Inner Straight Waveguides (Center Stack)
    wg_inner = gf.components.straight(length=L_straight, cross_section=xs_inner)
    
    # Place the three inner lines
    for y in [y_inner_bot, y_inner_mid, y_inner_top]:
        ref = c << wg_inner
        ref.center = (L_total/2, y)

    # 2. Outer Straight Waveguides
    wg_outer = gf.components.straight(length=L_straight, cross_section=xs_outer)
    
    ref_os_top = c << wg_outer
    ref_os_top.center = (L_total/2, y_outer_top_s)
    
    ref_os_bot = c << wg_outer
    ref_os_bot.center = (L_total/2, y_outer_bot_s)

    # 3. Flaring Bends (S-bends)
    # Create the S-bend primitive
    bend_flare = gf.components.bend_s(size=(L_bend, dy), cross_section=xs_outer)

    # Top Right: Connects to straight section, bends Up/Out
    # Note: bend_s goes from (0,0) to (size_x, size_y). 
    b_tr = c << bend_flare
    b_tr.connect("o1", ref_os_top.ports["o2"])

    # Top Left: Mirror Horizontally (Flip X)
    b_tl = c << bend_flare
    b_tl.mirror(p1=(0,0), p2=(0,1)) 
    b_tl.connect("o1", ref_os_top.ports["o1"])

    # Bottom Right: Mirror Vertically (Flip Y) to bend Down/Out
    b_br = c << bend_flare
    b_br.mirror(p1=(0,0), p2=(1,0))
    b_br.connect("o1", ref_os_bot.ports["o2"])

    # Bottom Left: Mirror X and Y
    b_bl = c << bend_flare
    b_bl.mirror(p1=(0,0), p2=(1,0)) # Flip Y
    b_bl.mirror(p1=(0,0), p2=(0,1)) # Flip X
    b_bl.connect("o1", ref_os_bot.ports["o1"])

    return c

if __name__ == "__main__":
    device = tapered_multi_coupler_v2()
    device.show()
    device.write_gds("tapered_coupler_v2.gds")