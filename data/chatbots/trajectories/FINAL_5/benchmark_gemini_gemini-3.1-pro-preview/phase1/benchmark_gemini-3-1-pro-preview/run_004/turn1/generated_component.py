import gdsfactory as gf

@gf.cell
def grating_coupler_device():
    """
    Parametric reconstruction of the symmetric grating-assisted contra-directional coupler.
    Footprint target: 18.24 x 0.7 um.
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    w_center = 0.06
    w_inner = 0.08
    w_outer = 0.08
    h_teeth = 0.05
    tooth_w = 0.05
    tooth_pitch = 0.1
    
    # 0.05 radius for U-turn perfectly fits the height constraints
    r_uturn = 0.05 
    L_straight = 12.0
    L_taper_inner = 3.12
    dx_shift = -6.0
    dy_shift = 0.16
    
    # Path coordinates for outer curved taper. 
    # Defined relative to base. Will be rotated by connection.
    p_curve_dy = -0.09 
    pts = [(0, 0), (1.5, 0), (2.5, p_curve_dy)]

    # --- Cross sections ---
    # Setting radius_min=0.01 explicitly prevents ValueError for tight bends like our 0.05um U-turn
    xs_inner = gf.cross_section.cross_section(width=w_inner, layer=(1, 0), radius_min=0.01)
    xs_outer = gf.cross_section.cross_section(width=w_outer, layer=(1, 0), radius_min=0.01)
    xs_tip = gf.cross_section.cross_section(width=0.001, layer=(1, 0), radius_min=0.01)

    # --- Reusable Sub-Component (Top Half) ---
    top_half = gf.Component("top_half")

    # 1. Inner straight waveguide (Grating backbone)
    inner_str = top_half << gf.components.straight(length=L_straight, cross_section=xs_inner)

    # 2. 180-Degree U-turn (on the right)
    uturn = top_half << gf.components.bend_circular(radius=r_uturn, angle=180, cross_section=xs_inner)
    uturn.connect('o1', inner_str.ports['o2'])

    # 3. Outer straight waveguide (Return path)
    outer_str = top_half << gf.components.straight(length=L_straight, cross_section=xs_outer)
    outer_str.connect('o1', uturn.ports['o2'])

    # 4. Inner straight taper (Extends furthest to the left)
    taper_inner = top_half << gf.components.taper(length=L_taper_inner, width1=w_inner, width2=0.001, layer=(1,0))
    taper_inner.connect('o1', inner_str.ports['o1'])

    # 5. Outer curved taper
    # We use path.smooth instead of bezier to ensure compatibility
    p = gf.path.smooth(pts, radius=0.4)
    trans = gf.path.transition(xs_outer, xs_tip, width_type='sine')
    curved_taper = top_half << gf.path.extrude_transition(p, trans)
    curved_taper.connect('o1', outer_str.ports['o2'])

    # 6. Grating Teeth Array
    tooth = gf.components.rectangle(size=(tooth_w, h_teeth), layer=(1,0), centered=False)
    y_tooth = -w_inner/2 - h_teeth
    n_teeth = int(L_straight / tooth_pitch)
    for i in range(n_teeth):
        t = top_half << tooth
        t.move((i * tooth_pitch, y_tooth))

    # --- Global Assembly ---
    
    # Place Top Half
    top_ref = c << top_half
    top_ref.move((dx_shift, dy_shift))

    # Place Bottom Half (Perfect 180-degree rotational symmetry)
    bot_ref = c << top_half
    bot_ref.rotate(180) # Rotates around its own internal origin prior to shifting
    bot_ref.move((-dx_shift, -dy_shift))

    # Central Isolation/Coupling Waveguide
    # Length ensures it spans the primary grating region nicely without exceeding footprint bounds
    c << gf.components.rectangle(size=(17.0, w_center), layer=(1,0), centered=True)

    return c

if __name__ == "__main__":
    device = grating_coupler_device()
    device.show()