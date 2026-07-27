import gdsfactory as gf
from gdsfactory.typings import LayerSpec

@gf.cell
def make_u_line_component(
    radius: float,
    L_horiz_u_arm: float,
    L_vert_u_arm: float,
    top_or_bottom: str, # "top" or "bottom"
    left_or_right: str, # "left" or "right"
    line_width: float,
    radius_min_override: float,
    layer: LayerSpec = (1, 0),
) -> gf.Component:
    """
    Creates a single U-shaped line segment composed of:
    - a horizontal straight section
    - an Euler bend
    - a vertical straight section (can be zero length)

    Args:
        radius: Centerline radius of the bend.
        L_horiz_u_arm: Length of the horizontal straight segment.
        L_vert_u_arm: Length of the vertical straight segment.
        top_or_bottom: Specifies if the U-arm is for the "top" or "bottom" block.
        left_or_right: Specifies if the U-arm is for the "left" or "right" side.
        line_width: Width of the waveguide.
        radius_min_override: Minimum bend radius allowed for the cross-section.
        layer: GDS layer for the component (LayerSpec tuple).
    """
    c = gf.Component()
    # Apply the radius_min_override to the cross_section
    xs = gf.cross_section.cross_section(width=line_width, layer=layer, radius_min=radius_min_override)

    s_h = c << gf.components.straight(length=L_horiz_u_arm, cross_section=xs)
    s_v = c << gf.components.straight(length=L_vert_u_arm, cross_section=xs)

    if top_or_bottom == "top":
        # Top U-arms bend downwards (CW turn when starting from +X or -X)
        bend = c << gf.components.bend_euler(radius=radius, angle=-90, cross_section=xs)
        if left_or_right == "left":
            # Horizontal segment points left, bend turns down from left, vertical segment points down
            s_h.rotate(180) # s_h.ports["o1"] is now on the right, s_h.ports["o2"] on the left
            bend.connect("o1", s_h.ports["o2"]) # Connect bend input to left end of horizontal
            s_v.connect("o1", bend.ports["o2"]) # Connect vertical input to bend output (downwards)
            c.add_port("port_h_connection", port=s_h.ports["o1"]) # Expose rightmost end of horizontal segment
            c.add_port("port_v_end", port=s_v.ports["o2"]) # Expose bottommost end of vertical segment
        else: # top-right
            # Horizontal segment points right, bend turns down from right, vertical segment points down
            bend.connect("o1", s_h.ports["o2"]) # Connect bend input to right end of horizontal
            s_v.connect("o1", bend.ports["o2"]) # Connect vertical input to bend output (downwards)
            c.add_port("port_h_connection", port=s_h.ports["o1"]) # Expose leftmost end of horizontal segment
            c.add_port("port_v_end", port=s_v.ports["o2"]) # Expose bottommost end of vertical segment
    else: # bottom
        # Bottom U-arms bend upwards (CCW turn when starting from +X or -X)
        bend = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
        if left_or_right == "left":
            # Horizontal segment points left, bend turns up from left, vertical segment points up
            s_h.rotate(180)
            bend.connect("o1", s_h.ports["o2"])
            s_v.connect("o1", bend.ports["o2"]) # Connect vertical input to bend output (upwards)
            c.add_port("port_h_connection", port=s_h.ports["o1"]) # Expose rightmost end of horizontal segment
            c.add_port("port_v_end", port=s_v.ports["o2"]) # Expose topmost end of vertical segment
        else: # bottom-right
            # Horizontal segment points right, bend turns up from right, vertical segment points up
            bend.connect("o1", s_h.ports["o2"])
            s_v.connect("o1", bend.ports["o2"]) # Connect vertical input to bend output (upwards)
            c.add_port("port_h_connection", port=s_h.ports["o1"]) # Expose leftmost end of horizontal segment
            c.add_port("port_v_end", port=s_v.ports["o2"]) # Expose topmost end of vertical segment
    return c


@gf.cell
def my_device(
    line_width: float = 0.2,
    line_gap: float = 0.092307,
    L_center_straight: float = 110.0,
    R_u_inner: float = 2.0,
    L_horiz_u_arm: float = 1.830772,
    L_vert_u_arm: float = 0.0,
    layer: LayerSpec = (1, 0),
) -> gf.Component:
    """
    Recreates the device geometry based on the provided image and footprint.

    Args:
        line_width: Width of each individual black line.
        line_gap: White gap between parallel lines.
        L_center_straight: Length of the central straight waveguide segments.
        R_u_inner: Radius of the innermost bend in the U-shaped arms.
        L_horiz_u_arm: Length of the horizontal straight segment of the U-arm
                       extending beyond the central straight region.
        L_vert_u_arm: Length of the vertical straight segment of the U-arm
                      (calculated to be 0 for exact vertical footprint match).
        layer: GDS layer for the components.
    """
    c = gf.Component("my_device")

    w = line_width
    g = line_gap
    
    # Set radius_min for the cross-sections to allow smaller bends.
    radius_min_for_cross_section = R_u_inner 

    # --- Calculate Y coordinates for the center of each line ---
    H_total = 14 * w + 13 * g 
    
    y_bottom_edge = -H_total / 2
    y_b_lines = [y_bottom_edge + w / 2 + i * (w + g) for i in range(5)]

    y_center_block_start_y = y_b_lines[4] + w/2 + g + w/2
    y_c_lines = [y_center_block_start_y + i * (w + g) for i in range(4)]

    y_top_block_start_y = y_c_lines[3] + w/2 + g + w/2
    y_t_lines = [y_top_block_start_y + i * (w + g) for i in range(5)]

    # --- Add Central straight lines ---
    for i in range(4):
        straight_ref = c << gf.components.straight(
            length=L_center_straight,
            cross_section=gf.cross_section.cross_section(
                width=w, layer=layer, radius_min=radius_min_for_cross_section
            )
        )
        straight_ref.center = (0, y_c_lines[i])

    # --- Add U-shaped lines ---
    x_left_connect = -L_center_straight / 2
    x_right_connect = L_center_straight / 2

    radii_u_arms = [R_u_inner + i * (w + g) for i in range(5)]

    # Top-Left U-arm group
    for i, r in enumerate(radii_u_arms):
        u_line = make_u_line_component(
            r, L_horiz_u_arm, L_vert_u_arm, "top", "left", w,
            radius_min_override=radius_min_for_cross_section,
            layer=layer
        )
        u_line_ref = c << u_line
        # FIX: Pass only the layer number (integer) to gf.Port, not the LayerSpec tuple.
        target_port = gf.Port("dummy", center=(x_left_connect, y_t_lines[i]), orientation=0, width=w, layer=layer[0])
        u_line_ref.connect("port_h_connection", target_port)

    # Top-Right U-arm group
    for i, r in enumerate(radii_u_arms):
        u_line = make_u_line_component(
            r, L_horiz_u_arm, L_vert_u_arm, "top", "right", w,
            radius_min_override=radius_min_for_cross_section,
            layer=layer
        )
        u_line_ref = c << u_line
        # FIX: Pass only the layer number (integer) to gf.Port.
        target_port = gf.Port("dummy", center=(x_right_connect, y_t_lines[i]), orientation=180, width=w, layer=layer[0])
        u_line_ref.connect("port_h_connection", target_port)

    # Bottom-Left U-arm group
    for i, r in enumerate(radii_u_arms):
        u_line = make_u_line_component(
            r, L_horiz_u_arm, L_vert_u_arm, "bottom", "left", w,
            radius_min_override=radius_min_for_cross_section,
            layer=layer
        )
        u_line_ref = c << u_line
        # FIX: Pass only the layer number (integer) to gf.Port.
        target_port = gf.Port("dummy", center=(x_left_connect, y_b_lines[i]), orientation=0, width=w, layer=layer[0])
        u_line_ref.connect("port_h_connection", target_port)

    # Bottom-Right U-arm group
    for i, r in enumerate(radii_u_arms):
        u_line = make_u_line_component(
            r, L_horiz_u_arm, L_vert_u_arm, "bottom", "right", w,
            radius_min_override=radius_min_for_cross_section,
            layer=layer
        )
        u_line_ref = c << u_line
        # FIX: Pass only the layer number (integer) to gf.Port.
        target_port = gf.Port("dummy", center=(x_right_connect, y_b_lines[i]), orientation=180, width=w, layer=layer[0])
        u_line_ref.connect("port_h_connection", target_port)

    return c

# Example usage and verification
if __name__ == "__main__":
    calculated_line_width = 0.2
    calculated_line_gap = 0.092307
    calculated_L_center_straight = 110.0
    calculated_R_u_inner = 2.0
    calculated_R_u_outermost = calculated_R_u_inner + 4 * (calculated_line_width + calculated_line_gap)
    calculated_L_horiz_u_arm = 1.830772
    calculated_L_vert_u_arm = 0.0

    print(f"Calculated line_width: {calculated_line_width}")
    print(f"Calculated line_gap: {calculated_line_gap}")
    print(f"Calculated L_center_straight: {calculated_L_center_straight}")
    print(f"Calculated R_u_inner: {calculated_R_u_inner}")
    print(f"Calculated R_u_outermost: {calculated_R_u_outermost}")
    print(f"Calculated L_horiz_u_arm: {calculated_L_horiz_u_arm}")
    print(f"Calculated L_vert_u_arm: {calculated_L_vert_u_arm}")
    print("-" * 30)

    device = my_device(
        line_width=calculated_line_width,
        line_gap=calculated_line_gap,
        L_center_straight=calculated_L_center_straight,
        R_u_inner=calculated_R_u_inner,
        L_horiz_u_arm=calculated_L_horiz_u_arm,
        L_vert_u_arm=calculated_L_vert_u_arm,
    )
    device.write_gds("my_device.gds")

    actual_width = calculated_L_center_straight + 2 * (calculated_L_horiz_u_arm + calculated_R_u_outermost)
    actual_height = (14 * calculated_line_width + 13 * calculated_line_gap) + 2 * calculated_L_vert_u_arm 

    print(f"Expected footprint W: 120.0")
    print(f"Actual calculated footprint W: {actual_width}")
    print(f"Expected footprint H: 4.0")
    print(f"Actual calculated footprint H: {actual_height}")
    
    bbox = device.bbox
    device_width_from_bbox = bbox[1][0] - bbox[0][0]
    device_height_from_bbox = bbox[1][1] - bbox[0][1]
    print(f"Device size (from GDSFactory bbox): Width={device_width_from_bbox}, Height={device_height_from_bbox}")
    
    # device.show() # Uncomment to open in KLayout