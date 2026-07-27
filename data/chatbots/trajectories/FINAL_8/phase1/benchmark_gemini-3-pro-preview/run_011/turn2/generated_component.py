import gdsfactory as gf

@gf.cell
def contra_directional_coupler_device():
    """
    Recreation of the device with corrected geometry and fill factors.
    Footprint constraint: 120um x 4um.
    """
    c = gf.Component()

    # =======================================================================
    # Parameters
    # =======================================================================
    # Dimensions adjusted for "Dense/Solid" look (High fill factor)
    wg_width = 0.2
    wg_gap = 0.05
    pitch = wg_width + wg_gap  # 0.25um pitch
    
    # Longitudinal dimensions
    total_length = 120.0
    bend_length = 15.0
    # The straight coupling region sits between the bends
    straight_length = total_length - (2 * bend_length) 
    
    # Vertical organization: 15 lines total to fill ~4um
    center_lines_count = 5
    outer_lines_count = 5
    
    # Gap between the center bundle and the outer bundles
    coupling_gap = 0.15 

    # Splay: How far the outer bundles move away at the input/output
    dy_splay = 1.0 

    # Create Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # =======================================================================
    # 1. Center Bundle (Straight, Full Length)
    # =======================================================================
    # Calculated to be centered at y=0
    # Range from -(N-1)/2 * pitch to +(N-1)/2 * pitch
    
    for i in range(center_lines_count):
        y = (i - (center_lines_count - 1) / 2) * pitch
        wg = c << gf.components.straight(length=total_length, cross_section=xs)
        wg.x = 0 # Center horizontally
        wg.y = y

    # =======================================================================
    # 2. Outer Bundles (Input Bend -> Straight -> Output Bend)
    # =======================================================================
    
    # Determine the Y-start offset for the outer bundles
    # Distance from y=0 to the center of the first outer waveguide
    y_center_max = ((center_lines_count - 1) / 2) * pitch
    y_outer_start_offset = y_center_max + wg_width + coupling_gap

    def add_outer_bundle(is_top=True):
        sign = 1.0 if is_top else -1.0
        
        for i in range(outer_lines_count):
            # Calculate Y position in the Straight Coupling Region
            # Stacking outwards from the center
            y_straight = sign * (y_outer_start_offset + i * pitch)

            # --- Middle Straight Section ---
            wg_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
            wg_straight.x = 0
            wg_straight.y = y_straight

            # --- Input Bend (Left Side) ---
            # Top Bundle: Must start high and come DOWN (\) to the straight section.
            # Bottom Bundle: Must start low and come UP (/) to the straight section.
            # Delta Y (End - Start) logic:
            # Top: Delta = -splay. Bottom: Delta = +splay.
            dy_in = -sign * dy_splay
            
            b_left = c << gf.components.bend_s(size=(bend_length, dy_in), cross_section=xs)
            # Connect the end of the bend (o2) to the start of the straight (o1)
            b_left.connect("o2", wg_straight.ports["o1"])

            # --- Output Bend (Right Side) ---
            # Top Bundle: Must go UP (/) away from center.
            # Bottom Bundle: Must go DOWN (\) away from center.
            # Delta Y logic:
            # Top: Delta = +splay. Bottom: Delta = -splay.
            dy_out = sign * dy_splay
            
            b_right = c << gf.components.bend_s(size=(bend_length, dy_out), cross_section=xs)
            b_right.connect("o1", wg_straight.ports["o2"])

    # Generate Top Group
    add_outer_bundle(is_top=True)
    
    # Generate Bottom Group
    add_outer_bundle(is_top=False)

    return c

# =======================================================================
# Build and Save
# =======================================================================
if __name__ == "__main__":
    device = contra_directional_coupler_device()
    device.show() 
    device.write_gds("contra_directional_coupler.gds")