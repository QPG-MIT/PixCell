import gdsfactory as gf

@gf.cell
def device_120_4_v5():
    """
    Creates a fan-in/fan-out device with a central bundle of waveguides 
    and two outer 'rail' bundles that mimic slotted solid blocks.
    Footprint: 120um x 4um.
    """
    c = gf.Component()

    # 1. Dimensions
    L = 120.0
    H = 4.0
    
    # Longitudinal sections (Target has distinct S-bends and a long straight center)
    l_bend = 30.0
    l_straight = L - 2 * l_bend  # 60.0

    # 2. Middle Bundle Parameters
    # 5 thin lines, straight through the center
    n_mid = 5
    w_mid = 0.1
    gap_mid = 0.12
    pitch_mid = w_mid + gap_mid  # 0.22
    
    xs_mid = gf.cross_section.cross_section(width=w_mid, layer=(1, 0))

    # Construct Middle Bundle
    # Centered at Y=0
    for i in range(n_mid):
        y = (i - (n_mid - 1) / 2.0) * pitch_mid
        s = c << gf.components.straight(length=L, cross_section=xs_mid)
        s.move((-L/2, y))

    # Calculate Top Edge of Middle Bundle (center of top line + half width)
    y_mid_top_edge = ((n_mid - 1) / 2.0) * pitch_mid + w_mid / 2.0  # ~0.49um

    # 3. Outer Bundle Parameters (Top and Bottom)
    # The target outer blocks look like solid shapes with 5 thin white slots.
    # We model this by drawing 6 wide "rails" (black) with narrow gaps (white).
    n_outer = 6
    w_outer = 0.16  # Wider rails for "blocky" appearance
    gap_outer = 0.08  # Thin gaps for the slot look
    pitch_outer = w_outer + gap_outer  # 0.24
    
    xs_outer = gf.cross_section.cross_section(width=w_outer, layer=(1, 0))

    # 4. Calculate Trajectories (Fan-In / Fan-Out)
    # The outer bundles are pushed to the edges (Y=2.0) at the ends (Fanned)
    # and pulled in close to the middle bundle at the center (Packed).

    # A. Fanned State (Ends):
    # Align top edge of Top Bundle to Device Limit (H/2 = 2.0)
    # Top Rail Center = 2.0 - w_outer/2.0
    y_fanned_top_rail_center = (H / 2.0) - (w_outer / 2.0)
    
    # Bottom Rail of Top Bundle (at Ends):
    y_fanned_bot_rail_center = y_fanned_top_rail_center - (n_outer - 1) * pitch_outer

    # B. Packed State (Center):
    # Align bottom edge of Top Bundle to clear the Middle Bundle
    # We use 'gap_mid' as clearance to maintain uniform spacing visual
    y_packed_bot_edge = y_mid_top_edge + gap_mid
    y_packed_bot_rail_center = y_packed_bot_edge + w_outer / 2.0

    # C. Displacement (dy)
    # How much the bundle moves vertically from Start (Edge) to Middle (Center)
    # Note: Moving from Edge -> Center is moving DOWN for the top bundle.
    # The S-bend component draws Left -> Right. 
    # Left (Edge) Y is High. Middle Y is Low. Right (Edge) Y is High.
    # So the first bend is Down (-dy), second bend is Up (+dy).
    dy = y_packed_bot_rail_center - y_fanned_bot_rail_center
    # dy should be negative

    # 5. Construct Top Bundle
    # Define the shape of a single rail trace
    trace_top = gf.Component("trace_top")
    
    # S-bend Down
    b1 = trace_top << gf.components.bend_s(size=(l_bend, dy), cross_section=xs_outer)
    # Straight
    st = trace_top << gf.components.straight(length=l_straight, cross_section=xs_outer)
    st.connect("o1", b1.ports["o2"])
    # S-bend Up (reverse displacement)
    b2 = trace_top << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs_outer)
    b2.connect("o1", st.ports["o2"])
    
    # Array the top rails
    for i in range(n_outer):
        # Calculate Y start position (Fanned state) for this rail
        # Rail i is offset from the bottom rail (index 0)
        y_local_offset = i * pitch_outer
        y_start = y_fanned_bot_rail_center + y_local_offset
        
        ref = c << trace_top
        ref.move((-L/2, y_start))

    # 6. Construct Bottom Bundle (Symmetric)
    # The bottom bundle is the mirror image. 
    # It starts Low, moves Up (Packed), then moves Low.
    
    trace_bot = gf.Component("trace_bot")
    # S-bend Up (Positive movement, which is -dy relative to the negative dy value)
    # Actually, we want to move from Y_fanned_bot (negative) to Y_packed_bot (closer to 0).
    # Since Y is negative, closer to 0 is an INCREASE in Y. 
    # The magnitude of shift is the same.
    shift_up = -dy # dy is negative, so this is positive
    
    b1b = trace_bot << gf.components.bend_s(size=(l_bend, shift_up), cross_section=xs_outer)
    stb = trace_bot << gf.components.straight(length=l_straight, cross_section=xs_outer)
    stb.connect("o1", b1b.ports["o2"])
    b2b = trace_bot << gf.components.bend_s(size=(l_bend, -shift_up), cross_section=xs_outer)
    b2b.connect("o1", stb.ports["o2"])

    # Array the bottom rails
    for i in range(n_outer):
        # We mirror the positions of the top bundle
        # Top bundle rail i corresponds to Bottom bundle rail i (mirrored)
        y_local_offset = i * pitch_outer
        # Top y: y_fanned_bot_rail_center + y_local_offset
        # Bot y: -(y_fanned_bot_rail_center + y_local_offset)
        y_start = -(y_fanned_bot_rail_center + y_local_offset)
        
        ref = c << trace_bot
        ref.move((-L/2, y_start))

    return c

if __name__ == "__main__":
    component = device_120_4_v5()
    component.write_gds("device_120_4_v5.gds")