import gdsfactory as gf

@gf.cell
def device_120_4():
    """
    Creates a directional coupler / fan-out device with a footprint of 120um x 4um.
    The device consists of a central straight bus and top/bottom waveguide bundles
    that curve in to couple with the center.
    """
    c = gf.Component()

    # Dimensions
    length = 120.0
    width_footprint = 4.0
    
    # Waveguide parameters
    # High density lines to match image features within 4um height
    wg_width = 0.15
    gap = 0.15
    pitch = wg_width + gap
    
    # Longitudinal sections geometry
    # The image shows curvature at the ends and a straight section in the middle
    l_taper = 30.0
    l_straight = length - 2 * l_taper
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # =========================================================================
    # 1. Middle Section (Straight Bundle)
    # =========================================================================
    # Consists of 2 straight parallel waveguides centered at y=0
    n_mid = 2
    # Calculate offsets to center the group
    mid_offsets = [(i - (n_mid-1)/2) * pitch for i in range(n_mid)]
    
    for y_off in mid_offsets:
        s = c << gf.components.straight(length=length, cross_section=xs)
        s.move(( -length/2, y_off )) # Center in x and y

    # Calculate boundary for coupling calculation
    y_mid_max = max(mid_offsets) + wg_width/2
    
    # =========================================================================
    # 2. Top Section (Curved Bundle)
    # =========================================================================
    # Consists of 3 waveguides that S-bend in and out
    n_top = 3
    
    # Calculate Bundle height geometry
    top_bundle_height = n_top * wg_width + (n_top - 1) * gap
    bundle_center_to_edge = top_bundle_height / 2
    
    # Determine Y positions
    # 1. Coupled position (Near center): defined by gap to middle bundle
    gap_coupling = 0.15
    y_top_near_edge = y_mid_max + gap_coupling
    y_top_center_near = y_top_near_edge + bundle_center_to_edge
    
    # 2. Input/Output position (Far): defined by footprint limit
    # Max Y allowed is width_footprint / 2
    y_top_max = width_footprint / 2
    y_top_center_far = y_top_max - bundle_center_to_edge
    
    # Calculate the vertical shift required (S-bend offset)
    dy = y_top_center_far - y_top_center_near # Positive value
    
    # Construct the Master Trace for the top arm
    # Shape: S-bend (down) -> Straight -> S-bend (up)
    # This trace starts at y=0 (relative), dips by -dy, then returns to 0
    c_trace_top = gf.Component("trace_top")
    
    # Part 1: S-bend down (coupling in)
    b1 = c_trace_top << gf.components.bend_s(size=(l_taper, -dy), cross_section=xs)
    
    # Part 2: Straight interaction region
    st = c_trace_top << gf.components.straight(length=l_straight, cross_section=xs)
    st.connect("o1", b1.ports["o2"])
    
    # Part 3: S-bend up (fan out)
    b2 = c_trace_top << gf.components.bend_s(size=(l_taper, dy), cross_section=xs)
    b2.connect("o1", st.ports["o2"])
    
    # Place the Top Bundle (Array of Master Traces)
    # Offsets relative to the bundle center
    top_offsets = [(i - (n_top-1)/2) * pitch for i in range(n_top)]
    
    for y_off in top_offsets:
        ref = c << c_trace_top
        # Start at x=-length/2.
        # Y position: The trace is built relative to "Far" Y (since net dy=0)
        ref.move(( -length/2, y_top_center_far + y_off ))

    # =========================================================================
    # 3. Bottom Section (Mirror of Top)
    # =========================================================================
    # 3 waveguides mirrored
    
    # Construct Master Trace for bottom arm
    # Shape: S-bend (up) -> Straight -> S-bend (down)
    c_trace_bot = gf.Component("trace_bot")
    
    # Part 1: S-bend up
    b1b = c_trace_bot << gf.components.bend_s(size=(l_taper, dy), cross_section=xs)
    
    # Part 2: Straight
    stb = c_trace_bot << gf.components.straight(length=l_straight, cross_section=xs)
    stb.connect("o1", b1b.ports["o2"])
    
    # Part 3: S-bend down
    b2b = c_trace_bot << gf.components.bend_s(size=(l_taper, -dy), cross_section=xs)
    b2b.connect("o1", stb.ports["o2"])
    
    # Place Bottom Bundle
    # Use symmetry: y_bot_center_far = -y_top_center_far
    y_bot_center_far = -y_top_center_far
    
    for y_off in top_offsets: # Same relative pitch offsets
        ref = c << c_trace_bot
        ref.move(( -length/2, y_bot_center_far + y_off ))

    return c

# Save the GDS
if __name__ == "__main__":
    component = device_120_4()
    component.write_gds("device_120_4.gds")