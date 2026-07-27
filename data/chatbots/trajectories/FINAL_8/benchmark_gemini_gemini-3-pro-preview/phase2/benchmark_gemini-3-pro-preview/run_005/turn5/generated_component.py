import gdsfactory as gf

@gf.cell
def dense_waveguide_coupler_concentric_refined():
    c = gf.Component()

    # --- 1. Dimensions & Constraints ---
    # Global length parameters
    total_length = 120.0
    x_right_edge = total_length / 2
    x_left_edge = -total_length / 2
    
    # Bend start X coordinate (distance from center)
    # The straight coupling regions (top/bottom) exist from edge to this coordinate
    x_bend_dist = 45.0
    x_bend_left = -x_bend_dist
    
    # Vertical extension length for the input/outputs
    v_len = 5.0

    # Dimensions for maximal density (Matching the thick black lines of target)
    width = 0.25
    gap = 0.1
    pitch = width + gap  # 0.35 um
    
    # Spacing between the center group and outer groups
    # Set equal to internal gap to create a uniform 'bus' look
    gap_inter_group = gap
    
    # Bend Radius Constraints
    # The inner-most track of the bends (smallest radius)
    r_min_inner_track = 2.0

    # Define Cross Section
    # Explicitly set radius_min small to allow our calculated concentric radii
    xs = gf.cross_section.cross_section(
        width=width, 
        radius_min=0.1, 
        layer=(1, 0)
    )

    # Number of lines per group
    n_lines = 4

    # --- 2. Center Group Construction ---
    # Centered at y=0, straight through lines running the full length
    y_offsets_c = [(i - (n_lines - 1) / 2) * pitch for i in range(n_lines)]
    
    for y in y_offsets_c:
        wg = c << gf.components.straight(length=total_length, cross_section=xs)
        wg.center = (0, y)

    # --- 3. Top Group Geometry Logic ---
    # Calculate Y positions for the Top Group
    y_center_max = y_offsets_c[-1] + width/2
    y_top_group_start = y_center_max + gap_inter_group
    
    # Y centers for Top group lines
    y_offsets_top = [(y_top_group_start + width/2) + i * pitch for i in range(n_lines)]
    
    # Calculate Common Center of Curvature Y (Y_cc) for Concentricity
    # For a turn UP (North), the inner track is the highest Y line.
    y_top_highest = y_offsets_top[-1]
    y_cc_top = y_top_highest + r_min_inner_track
    
    # --- 4. Assembly Loop (Quadrants) ---
    for y in y_offsets_top:
        # --- Radius Calculation ---
        # Concentric bends share a center of curvature.
        # r = Y_center_of_curvature - Y_waveguide
        r = y_cc_top - y
        
        # Length of horizontal straight segment (from edge to bend)
        l_horiz = abs(x_left_edge - x_bend_left)

        # -- A. Top Left Quadrant --
        # Bend: Input from Left, turning UP
        b_tl = c << gf.components.bend_circular(radius=r, angle=90, cross_section=xs)
        b_tl.move((x_bend_left, y))
        
        # Horizontal Straight (Input from Left Edge)
        s_h_tl = c << gf.components.straight(length=l_horiz, cross_section=xs)
        s_h_tl.connect("o2", b_tl.ports["o1"])
        
        # Vertical Straight (Output Upwards)
        s_v_tl = c << gf.components.straight(length=v_len, cross_section=xs)
        s_v_tl.connect("o1", b_tl.ports["o2"])

        # -- B. Top Right Quadrant --
        # Mirror Top Left horizontally
        b_tr = c << gf.components.bend_circular(radius=r, angle=90, cross_section=xs)
        b_tr.move((x_bend_left, y)) # Place at TL position
        b_tr.mirror_x()             # Mirror to Right side
        
        s_h_tr = c << gf.components.straight(length=l_horiz, cross_section=xs)
        s_h_tr.connect("o1", b_tr.ports["o1"]) # Connect straight to the input
        
        s_v_tr = c << gf.components.straight(length=v_len, cross_section=xs)
        s_v_tr.connect("o1", b_tr.ports["o2"])

        # -- C. Bottom Left Quadrant --
        # Mirror Top Left vertically
        b_bl = c << gf.components.bend_circular(radius=r, angle=90, cross_section=xs)
        b_bl.move((x_bend_left, y))
        b_bl.mirror_y() # Mirror to Bottom
        
        s_h_bl = c << gf.components.straight(length=l_horiz, cross_section=xs)
        s_h_bl.connect("o2", b_bl.ports["o1"])
        
        s_v_bl = c << gf.components.straight(length=v_len, cross_section=xs)
        s_v_bl.connect("o1", b_bl.ports["o2"])

        # -- D. Bottom Right Quadrant --
        # Mirror Top Right vertically (or Top Left XY)
        b_br = c << gf.components.bend_circular(radius=r, angle=90, cross_section=xs)
        b_br.move((x_bend_left, y))
        b_br.mirror_x()
        b_br.mirror_y()
        
        s_h_br = c << gf.components.straight(length=l_horiz, cross_section=xs)
        s_h_br.connect("o1", b_br.ports["o1"])
        
        s_v_br = c << gf.components.straight(length=v_len, cross_section=xs)
        s_v_br.connect("o1", b_br.ports["o2"])

    return c

if __name__ == "__main__":
    device = dense_waveguide_coupler_concentric_refined()
    device.write_gds("dense_coupler_refined.gds")