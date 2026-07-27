import gdsfactory as gf

@gf.cell
def parametric_racetrack_device():
    # Main component container
    c = gf.Component("Racetrack_Device")
    layer = (1, 0)

    # ==========================================
    # 1. Parametric Variables (Footprint 3.0 x 5.5)
    # ==========================================
    R_out = 1.5             # Outer radius (Total Height = 3.0)
    L_total = 5.5           # Total width
    L = L_total - 2 * R_out # Straight section length (2.5)

    W_bend = 0.5            # Width of the track at the bends
    R_in = R_out - W_bend   # Inner radius (1.0)
    W_thick = 1.0           # Width of the thickened straight track sections

    H_mid_hole = 2 * (R_out - W_thick) # Height of central narrow hole gap (1.0)
    H_end_hole = 2 * R_in              # Height of hole near bends (2.0)

    L_mid_thick = 1.4       # Length of the central thick track region
    L_taper = 0.4           # Length of the taper transitions
    # Remaining straight length before the bend circles
    L_end_straight = (L - L_mid_thick - 2 * L_taper) / 2 # 0.15

    # Dimensions for the 4 inner rectangular cuts
    L_cut = 0.45
    H_cut = 0.5
    Gap_cut = 0.2
    X_cut = Gap_cut / 2 + L_cut / 2    # X-center of cuts (0.325)
    Y_cut = 1.0                        # Y-center of top track ((1.5 + 0.5)/2)

    # ==========================================
    # 2. Build Positive Geometry (Solid Stadium)
    # ==========================================
    stadium = gf.Component("Solid_Stadium")
    stadium << gf.components.rectangle(size=(L, 2*R_out), centered=True, layer=layer)
    
    # Left and Right semi-circles
    (stadium << gf.components.circle(radius=R_out, layer=layer)).movex(-L/2)
    (stadium << gf.components.circle(radius=R_out, layer=layer)).movex(L/2)

    # ==========================================
    # 3. Build Negative Geometry (Holes to Subtract)
    # ==========================================
    holes = gf.Component("Holes")

    # --- 3a. Inner Central Profile ---
    c_hole = gf.Component("Central_Hole")
    
    xs_mid = gf.cross_section.cross_section(width=H_mid_hole, layer=layer)
    xs_end = gf.cross_section.cross_section(width=H_end_hole, layer=layer)

    mid_str = gf.components.straight(length=L_mid_thick, cross_section=xs_mid)
    taper = gf.components.taper(length=L_taper, width1=H_mid_hole, width2=H_end_hole, layer=layer)
    end_str = gf.components.straight(length=L_end_straight, cross_section=xs_end)
    circ_in = gf.components.circle(radius=R_in, layer=layer)

    # Assemble central polygon using port connections
    m_ref = c_hole << mid_str
    m_ref.move((-L_mid_thick/2, 0)) # Center the middle block

    tl_ref = c_hole << taper
    tl_ref.connect('o1', m_ref.ports['o1'])  # Connects and expands leftwards

    tr_ref = c_hole << taper
    tr_ref.connect('o1', m_ref.ports['o2'])  # Connects and expands rightwards

    el_ref = c_hole << end_str
    el_ref.connect('o2', tl_ref.ports['o2']) # Extends the wide end further left

    er_ref = c_hole << end_str
    er_ref.connect('o1', tr_ref.ports['o2']) # Extends the wide end further right

    # End void circles mapped perfectly to the endpoints to create uniform bends
    (c_hole << circ_in).move(el_ref.ports['o1'].center)
    (c_hole << circ_in).move(er_ref.ports['o2'].center)

    holes << c_hole

    # --- 3b. Four Rectangular Track Cuts ---
    cut = gf.components.rectangle(size=(L_cut, H_cut), centered=True, layer=layer)
    
    (holes << cut).move((-X_cut, Y_cut))   # Top-Left
    (holes << cut).move((X_cut, Y_cut))    # Top-Right
    (holes << cut).move((-X_cut, -Y_cut))  # Bottom-Left
    (holes << cut).move((X_cut, -Y_cut))   # Bottom-Right

    # ==========================================
    # 4. Final Boolean Subtraction
    # ==========================================
    # Subtracting the complex 'holes' assembly from the solid 'stadium' 
    final_shape = gf.boolean(A=stadium, B=holes, operation='not', layer=layer)
    c << final_shape

    return c

if __name__ == "__main__":
    # Create and output the GDS file
    device = parametric_racetrack_device()
    device.write_gds("device.gds")