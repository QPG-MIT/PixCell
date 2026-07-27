import gdsfactory as gf

# Define global parameters derived from footprint and visual inspection
w = 0.1  # Feature width in um, derived from total height 0.7um / 7 segments
dy_bend_span = 1.5 * w # Vertical span between H1/H2 (and H4/H5) = 0.15 um
R_bend = dy_bend_span / 2  # Radius of the 90-degree turns forming the C-bend = 0.075 um

# The target overall device width (from footprint constraint)
L_total_footprint_width = 18.24
# The length of the straight segments inside the bends
internal_straight_length = L_total_footprint_width - 2 * R_bend # 18.24 - 2*0.075 = 18.09 um


@gf.cell
def custom_u_bend(bend_radius: float, dy_span: float, cross_section, direction: str):
    """
    Creates a C-bend component that connects two parallel waveguides
    at the same x-coordinate but different y-coordinates, curving outwards.

    Args:
        bend_radius: Radius of the 90-degree turns that form the C-bend.
        dy_span: The vertical distance between the two connected waveguide centers.
                 (e.g., y_H1 - y_H2). For this design, dy_span = 2 * bend_radius.
        cross_section: The cross-section for the waveguide.
        direction: "left" or "right" indicating the side of the device the bend is on.
                   "left" connects ports facing 180 degrees (left).
                   "right" connects ports facing 0 degrees (right).
    """
    c = gf.Component()
    p = gf.Path()

    # The length of the vertical straight segment between the two 90-degree bends.
    # For this specific design, dy_span = 1.5 * w = 0.15, and bend_radius = dy_span / 2 = 0.075.
    # So, dy_span - 2 * bend_radius = 0.15 - 2 * 0.075 = 0.
    # We add a small tolerance for floating point comparisons.
    vertical_straight_length = dy_span - 2 * bend_radius
    
    if direction == "left":
        # Path starts at (0,0) with initial orientation 180 (left)
        p.append(gf.path.straight(length=bend_radius))  # 1. Go left (outwards)
        # From 180 (left) to 270 (down) is a 90-degree counter-clockwise turn
        p.append(gf.path.euler(radius=bend_radius, angle=90)) # 2. Turn down
        if vertical_straight_length > 1e-9: # Only add if significant
            p.append(gf.path.straight(length=vertical_straight_length)) # 3. Vertical segment
        # From 270 (down) to 180 (left) is a 90-degree counter-clockwise turn
        p.append(gf.path.euler(radius=bend_radius, angle=90)) # 4. Turn left (inwards)
        p.append(gf.path.straight(length=bend_radius)) # 5. Go right, returning to initial x-coordinate
        
    elif direction == "right":
        # Path starts at (0,0) with initial orientation 0 (right)
        p.append(gf.path.straight(length=bend_radius))  # 1. Go right (outwards)
        # From 0 (right) to 270 (down) is a 90-degree clockwise turn
        p.append(gf.path.euler(radius=bend_radius, angle=-90)) # 2. Turn down
        if vertical_straight_length > 1e-9: # Only add if significant
            p.append(gf.path.straight(length=vertical_straight_length)) # 3. Vertical segment
        # From 270 (down) to 0 (right) is a 90-degree clockwise turn
        p.append(gf.path.euler(radius=bend_radius, angle=-90)) # 4. Turn right (inwards)
        p.append(gf.path.straight(length=bend_radius)) # 5. Go left, returning to initial x-coordinate
    else:
        raise ValueError("Direction must be 'left' or 'right'")

    # Extrude the path to create the component geometry
    u_bend_ref = c << gf.path.extrude(p, cross_section=cross_section)
    
    # Define ports for the custom component
    # Port 0 (first port) is at the start of the path (0,0)
    # Port 1 (second port) is at the end of the path (0, -dy_span)
    c.add_port("o1", port=u_bend_ref.ports[0])
    c.add_port("o2", port=u_bend_ref.ports[1])
    return c

@gf.cell
def device_from_image():
    c = gf.Component()

    # Common cross-section
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))

    # Y-coordinates for horizontal segments (center-to-center)
    # H1 top edge is y_H1 + w/2 = 3.5w = 0.35um. H5 bottom edge is y_H5 - w/2 = -3.5w = -0.35um.
    # Total height = 0.35 - (-0.35) = 0.7um, which matches the constraint.
    y_H3 = 0
    y_H2 = 1.5 * w  # Upper comb base
    y_H1 = 3.0 * w  # Outermost upper line
    # Bottom segments are mirrored
    y_H4 = -y_H2
    y_H5 = -y_H1
    
    # Comb teeth parameters
    num_teeth = 25
    tooth_width = w
    tooth_spacing = w # Visually, gaps appear equal to width
    L_comb_teeth = num_teeth * tooth_width + (num_teeth - 1) * tooth_spacing # 25*0.1 + 24*0.1 = 4.9 um

    # Calculate starting x-coordinate for the combs.
    # The combs are centered within the `internal_straight_length` span, which starts at R_bend.
    x_start_straight_segments = R_bend
    x_end_straight_segments = x_start_straight_segments + internal_straight_length
    
    # The comb section itself spans L_comb_teeth.
    # The center of the internal straight section is at x_start_straight_segments + internal_straight_length / 2.
    # The center of the comb section is also there.
    x_start_teeth = x_start_straight_segments + (internal_straight_length - L_comb_teeth) / 2


    # 1. Central Straight (H3)
    h3_wg = c << gf.components.straight(length=internal_straight_length, cross_section=xs)
    h3_wg.xmin = x_start_straight_segments
    h3_wg.y = y_H3

    # 2. Top Comb (H2 + teeth)
    h2_wg = c << gf.components.straight(length=internal_straight_length, cross_section=xs)
    h2_wg.xmin = x_start_straight_segments
    h2_wg.y = y_H2
    
    tooth_rect = gf.components.rectangle(size=(tooth_width, tooth_width), layer=xs.layer)
    for i in range(num_teeth):
        tooth_ref = c << tooth_rect
        # Teeth point down from the bottom edge of H2
        tooth_ref.xmin = x_start_teeth + i * (tooth_width + tooth_spacing)
        tooth_ref.ymax = h2_wg.ymin 

    # 3. Bottom Comb (H4 + teeth)
    h4_wg = c << gf.components.straight(length=internal_straight_length, cross_section=xs)
    h4_wg.xmin = x_start_straight_segments
    h4_wg.y = y_H4
    
    for i in range(num_teeth):
        tooth_ref = c << tooth_rect
        # Teeth point up from the top edge of H4
        tooth_ref.xmin = x_start_teeth + i * (tooth_width + tooth_spacing)
        tooth_ref.ymin = h4_wg.ymax

    # 4. Outermost Horizontal Lines (H1, H5)
    h1_wg = c << gf.components.straight(length=internal_straight_length, cross_section=xs)
    h1_wg.xmin = x_start_straight_segments
    h1_wg.y = y_H1

    h5_wg = c << gf.components.straight(length=internal_straight_length, cross_section=xs)
    h5_wg.xmin = x_start_straight_segments
    h5_wg.y = y_H5

    # 5. Connecting Bends (C-shapes)
    # Create the bend components
    bend_left_top_comp = custom_u_bend(R_bend, dy_bend_span, xs, direction="left")
    bend_right_top_comp = custom_u_bend(R_bend, dy_bend_span, xs, direction="right")
    bend_left_bottom_comp = custom_u_bend(R_bend, dy_bend_span, xs, direction="left")
    bend_right_bottom_comp = custom_u_bend(R_bend, dy_bend_span, xs, direction="right")

    # Connect Top-Left bend (H1.o1 to H2.o1)
    # The bend's 'o1' connects to H1's 'o1'. The bend's 'o2' then connects to H2's 'o1'.
    b_lt_ref = c << bend_left_top_comp
    b_lt_ref.connect("o1", h1_wg.ports["o1"])
    h2_wg.connect("o1", b_lt_ref.ports["o2"]) 

    # Connect Bottom-Left bend (H5.o1 to H4.o1)
    b_lb_ref = c << bend_left_bottom_comp
    b_lb_ref.connect("o1", h5_wg.ports["o1"])
    h4_wg.connect("o1", b_lb_ref.ports["o2"]) 

    # Connect Top-Right bend (H1.o2 to H2.o2)
    b_rt_ref = c << bend_right_top_comp
    b_rt_ref.connect("o1", h1_wg.ports["o2"])
    h2_wg.connect("o2", b_rt_ref.ports["o2"]) 

    # Connect Bottom-Right bend (H5.o2 to H4.o2)
    b_rb_ref = c << bend_right_bottom_comp
    b_rb_ref.connect("o1", h5_wg.ports["o2"])
    h4_wg.connect("o2", b_rb_ref.ports["o2"]) 

    return c

# Create the device
device = device_from_image()

# Check the footprint against the specified constraints
calculated_width = round(device.xmax - device.xmin, 2)
calculated_height = round(device.ymax - device.ymin, 2)

expected_width_final = L_total_footprint_width # 18.24
expected_height_final = 0.7

print(f"Calculated Footprint (Final Check): [{calculated_width}, {calculated_height}]")
print(f"Expected Footprint (From Task): [{expected_width_final}, {expected_height_final}]")
assert calculated_width == expected_width_final, f"Width mismatch: {calculated_width} != {expected_width_final}"
assert calculated_height == expected_height_final, f"Height mismatch: {calculated_height} != {expected_height_final}"
print("Footprint matches expected values after adjustments.")

# Optional: To visualize the layout
# device.write_gds("image_device.gds")
# device.show() # Requires KLayout to be installed and in PATH