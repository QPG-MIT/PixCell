import gdsfactory as gf

@gf.cell
def swg_directional_coupler():
    """
    Parametric recreation of the SWG directional coupler.
    Built entirely from GDSFactory catalog primitives and path transitions.
    """
    c = gf.Component("swg_coupler")

    # --- Global Geometrical Parameters ---
    w = 0.08              # Waveguide and SWG block width
    w_tip = 0.005         # Sharp point width for the outer tapers
    gap = 0.04            # Gap between solid lines and SWG lines
    R_bend = 0.06         # U-bend radius (matches w/2 + gap + w/2)
    
    # --- Y-Coordinates (Height Constraint: exactly 0.7 µm) ---
    y_center = 0.0
    y_top_swg = 0.12      # Center to Top SWG distance
    y_top_arm = 0.24      # Top SWG to Top Arm distance
    y_bot_swg = -0.12
    y_bot_arm = -0.24
    
    # Outer tips reach exactly +/- 0.35 to satisfy the 0.7um height constraint
    y_max = 0.35 
    
    # --- X-Coordinates (Width Constraint: exactly 18.24 µm) ---
    x_tip = 9.12          # 18.24 / 2
    x_ubend_top = 7.0     # X-coordinate where the Top U-bend starts
    x_ubend_bot = -7.0    # X-coordinate where the Bottom U-bend starts
    x_taper_start = 6.0   # X-coordinate where straight arms begin to taper outwards
    L_taper = x_tip - x_taper_start

    # --- Cross Sections ---
    # radius_min=0.0 is required to allow tight sub-micron U-bends
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0), radius_min=0.0)
    xs_tip = gf.cross_section.cross_section(width=w_tip, layer=(1, 0), radius_min=0.0)

    # --- 1. Central Isolation Line ---
    x_c_edge = x_ubend_top + R_bend + w/2  # Align center line with outer bend edge
    center_line = gf.components.straight(length=2 * x_c_edge, cross_section=xs)
    center_ref = c << center_line
    center_ref.move((-x_c_edge, y_center))

    # --- 2. U-Bends ---
    # Top Right U-bend (Curves right-to-left downward)
    bend_top = gf.components.bend_circular(radius=R_bend, angle=-180, cross_section=xs)
    b_top_ref = c << bend_top
    b_top_ref.move((x_ubend_top, y_top_arm))

    # Bottom Left U-bend (Curves left-to-right upward)
    bend_bot = gf.components.bend_circular(radius=R_bend, angle=-180, cross_section=xs)
    b_bot_ref = c << bend_bot
    b_bot_ref.rotate(180) # Rotate the instance, not the base component
    b_bot_ref.move((x_ubend_bot, y_bot_arm))

    # --- 3. Straight Arms ---
    # Top arm spans from left taper connection to right U-bend
    L_top_arm = x_ubend_top - (-x_taper_start)
    arm_top = gf.components.straight(length=L_top_arm, cross_section=xs)
    arm_top_ref = c << arm_top
    arm_top_ref.move((-x_taper_start, y_top_arm))

    # Bottom arm spans from left U-bend to right taper connection
    L_bot_arm = x_taper_start - x_ubend_bot
    arm_bot = gf.components.straight(length=L_bot_arm, cross_section=xs)
    arm_bot_ref = c << arm_bot
    arm_bot_ref.move((x_ubend_bot, y_bot_arm))

    # --- 4. Subwavelength Grating (SWG) Arrays ---
    pitch = 0.12
    block_len = 0.06
    num_blocks = int(14.0 / pitch) # Fits perfectly in the 14um central span
    
    # Create a base block to reference multiple times
    base_block = gf.components.rectangle(size=(block_len, w), layer=(1, 0), centered=True)
    
    for i in range(num_blocks):
        # Top SWG (Spanning right to left)
        bx = x_ubend_top - (block_len / 2) - i * pitch
        b_t_ref = c << base_block
        b_t_ref.move((bx, y_top_swg))
        
        # Bottom SWG (Spanning left to right)
        bx_bot = x_ubend_bot + (block_len / 2) + i * pitch
        b_b_ref = c << base_block
        b_b_ref.move((bx_bot, y_bot_swg))

    # --- 5. Asymmetric Outer Tapers ---
    # Using smooth Bezier paths to recreate the horn-like flare at the ends.
    # We calculate dy such that the outer edge of the tip perfectly aligns with y_max.
    dy = y_max - (w_tip / 2) - y_top_arm
    
    # Top-Left Taper (Extending backwards to the left)
    p_top = gf.path.bezier([(0, 0), (-L_taper*0.4, 0), (-L_taper*0.7, dy), (-L_taper, dy)])
    trans_top = gf.path.transition(xs, xs_tip, width_type='sine')
    taper_top = gf.path.extrude_transition(p_top, trans_top)
    taper_top_ref = c << taper_top
    taper_top_ref.move((-x_taper_start, y_top_arm))

    # Bottom-Right Taper (Extending forwards to the right)
    p_bot = gf.path.bezier([(0, 0), (L_taper*0.4, 0), (L_taper*0.7, -dy), (L_taper, -dy)])
    taper_bot = gf.path.extrude_transition(p_bot, trans_top)
    taper_bot_ref = c << taper_bot
    taper_bot_ref.move((x_taper_start, y_bot_arm))

    return c

if __name__ == "__main__":
    c = swg_directional_coupler()
    c.show()