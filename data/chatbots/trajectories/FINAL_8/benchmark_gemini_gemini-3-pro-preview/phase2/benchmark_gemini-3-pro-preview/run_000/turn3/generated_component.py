import gdsfactory as gf

@gf.cell
def device_120_4_v3():
    """
    Creates a fan-in/fan-out device with 3 bundles of 4 waveguides.
    Footprint: 120um x 4um.
    The top and bottom bundles curve inwards to couple with the straight middle bundle.
    Optimized for visible curvature within tight vertical constraints.
    """
    c = gf.Component()

    # ---------------------------------------------------------
    # 1. Dimensions & Constraints
    # ---------------------------------------------------------
    L = 120.0
    H = 4.0
    
    # Waveguide Parameters
    # We use slightly narrower waveguides to allow more vertical space 
    # for the fan-out bends within the 4um limit.
    width = 0.15
    gap = 0.1
    pitch = width + gap
    n_lines = 4  # Lines per bundle
    
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # Longitudinal Sections
    # Target image shows a long straight section and sharper bends.
    l_bend = 25.0
    l_straight = L - 2 * l_bend  # 70.0
    
    # Bundle Height Calculation
    # Height of one bundle of 4 lines
    h_bundle = n_lines * width + (n_lines - 1) * gap  # 4*0.15 + 3*0.1 = 0.9 um

    # ---------------------------------------------------------
    # 2. Vertical Position Calculations
    # ---------------------------------------------------------
    # Middle Bundle is centered at Y=0.
    
    # Calculate positions for the Top Bundle:
    
    # A. "Packed" Position (Center of device): 
    # Stacked on top of Middle bundle with uniform gap spacing.
    # This creates a solid block of lines in the center.
    y_mid_max = h_bundle / 2.0
    y_top_packed = y_mid_max + gap + (h_bundle / 2.0)
    
    # B. "Fanned" Position (Edges of device):
    # Pushed to the absolute limit of the 4um footprint (Y=+2.0)
    # to maximize the bend curvature.
    y_top_max_limit = H / 2.0
    y_top_fanned = y_top_max_limit - (h_bundle / 2.0)
    
    # Vertical shift (dy) for the S-bends
    # Top bundle moves DOWN from Fanned to Packed.
    dy = y_top_packed - y_top_fanned  # Negative value
    
    # ---------------------------------------------------------
    # 3. Middle Bundle (Straight)
    # ---------------------------------------------------------
    for i in range(n_lines):
        y_off = (i - (n_lines - 1) / 2.0) * pitch
        s = c << gf.components.straight(length=L, cross_section=xs)
        s.move((-L/2, y_off))

    # ---------------------------------------------------------
    # 4. Top Bundle (Bend -> Straight -> Bend)
    # ---------------------------------------------------------
    # Construct a single trace shape
    trace_top = gf.Component("trace_top")
    
    # Part 1: S-bend moving IN (down) from Fanned to Packed
    b1 = trace_top << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    
    # Part 2: Straight interaction region
    st = trace_top << gf.components.straight(length=l_straight, cross_section=xs)
    st.connect("o1", b1.ports["o2"])
    
    # Part 3: S-bend moving OUT (up) from Packed to Fanned
    # We use -dy to reverse the displacement (move up)
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
    trace_bot = gf.Component("trace_bot")
    
    # Bottom bundle moves UP from Fanned (low) to Packed (higher)
    # This is a positive displacement of magnitude |dy|
    # Since dy is negative, -dy is positive.
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
    component = device_120_4_v3()
    component.write_gds("device_120_4_v3.gds")