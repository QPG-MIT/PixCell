import gdsfactory as gf

@gf.cell
def device_120_4_v2():
    """
    Creates a fan-in/fan-out device with 3 bundles of 4 waveguides.
    Footprint: 120um x 4um.
    The top and bottom bundles curve inwards to couple with the straight middle bundle.
    """
    c = gf.Component()

    # ---------------------------------------------------------
    # 1. Dimensions & Constraints
    # ---------------------------------------------------------
    # Footprint: 120um x 4um
    L = 120.0
    H = 4.0
    
    # Longitudinal Sections
    # Total length 120 divided into: 30 (bend) + 60 (straight) + 30 (bend)
    l_bend = 30.0
    l_straight = L - 2 * l_bend
    
    # Waveguide Parameters
    # To fit 12 waveguides vertically in 4um with high density:
    # 3 bundles * 4 lines = 12 lines total
    width = 0.2
    gap = 0.1
    pitch = width + gap
    n_lines = 4  # Lines per bundle
    
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # Bundle Height Calculation
    # Height of one bundle of 4 lines
    h_bundle = n_lines * width + (n_lines - 1) * gap  # 4*0.2 + 3*0.1 = 1.1 um

    # ---------------------------------------------------------
    # 2. Vertical Position Calculations
    # ---------------------------------------------------------
    # Middle Bundle: Centered at Y=0
    
    # Top Bundle Calculation:
    # 1. "Packed" Position (Center): Stacked directly on top of Middle with 'gap'
    #    The middle bundle extends from -h/2 to +h/2.
    y_mid_max = h_bundle / 2
    y_top_packed = y_mid_max + gap + (h_bundle / 2)
    
    # 2. "Fanned" Position (Ends): Pushed to the limit of the 4um footprint (Y=+2.0)
    #    The top bundle extends down from +2.0.
    y_top_max_limit = H / 2  # 2.0
    y_top_fanned = y_top_max_limit - (h_bundle / 2)
    
    # Vertical shift (dy) for the S-bends
    # The Top bundle starts at 'Fanned', moves to 'Packed', then back to 'Fanned'.
    # dy is the displacement for the first bend.
    dy = y_top_packed - y_top_fanned  # Expected to be negative (moving down)
    
    # ---------------------------------------------------------
    # 3. Middle Bundle (Straight)
    # ---------------------------------------------------------
    # 4 straight waveguides centered at Y=0
    for i in range(n_lines):
        # Calculate offset relative to bundle center
        y_off = (i - (n_lines - 1) / 2.0) * pitch
        s = c << gf.components.straight(length=L, cross_section=xs)
        s.move((-L/2, y_off))

    # ---------------------------------------------------------
    # 4. Top Bundle (S-Bend -> Straight -> S-Bend)
    # ---------------------------------------------------------
    # Construct a single trace shape first
    trace_top = gf.Component("trace_top")
    
    # Part 1: S-bend moving IN (down) from Fanned to Packed
    b1 = trace_top << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    
    # Part 2: Straight interaction region
    st = trace_top << gf.components.straight(length=l_straight, cross_section=xs)
    st.connect("o1", b1.ports["o2"])
    
    # Part 3: S-bend moving OUT (up) from Packed to Fanned
    # We use -dy to reverse the displacement
    b2 = trace_top << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    b2.connect("o1", st.ports["o2"])
    
    # Array the Top Bundle
    for i in range(n_lines):
        y_off = (i - (n_lines - 1) / 2.0) * pitch
        ref = c << trace_top
        # Position relative to the Fanned start point at the left edge
        ref.move((-L/2, y_top_fanned + y_off))

    # ---------------------------------------------------------
    # 5. Bottom Bundle (Mirrored)
    # ---------------------------------------------------------
    # Construct trace for bottom arm
    trace_bot = gf.Component("trace_bot")
    
    # For the bottom bundle:
    # Starts at negative fanned position, moves UP to negative packed position.
    # Displacement is positive (opposite of top's dy).
    b1b = trace_bot << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    
    stb = trace_bot << gf.components.straight(length=l_straight, cross_section=xs)
    stb.connect("o1", b1b.ports["o2"])
    
    # Moves back DOWN
    b2b = trace_bot << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    b2b.connect("o1", stb.ports["o2"])
    
    # Array the Bottom Bundle
    y_bot_fanned = -y_top_fanned
    for i in range(n_lines):
        y_off = (i - (n_lines - 1) / 2.0) * pitch
        ref = c << trace_bot
        ref.move((-L/2, y_bot_fanned + y_off))

    return c

if __name__ == "__main__":
    component = device_120_4_v2()
    component.write_gds("device_120_4_v2.gds")