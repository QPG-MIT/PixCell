import gdsfactory as gf

@gf.cell
def device_recreated():
    """
    Recreation of the racetrack device with slotted straight sections.
    Footprint constraint: 3.0um x 5.5um.
    """
    c = gf.Component()
    
    # =======================================================================
    # 1. Define Parameters
    # =======================================================================
    # External Constraints
    total_height = 3.0
    total_length = 5.5
    
    # Internal Geometries estimated from visual proportions
    track_width = 0.8
    
    # Derived Dimensions
    # R_outer is half the height (1.5um)
    # The center radius (for the path) is R_outer - half_width
    r_center = (total_height / 2.0) - (track_width / 2.0)  # 1.1um
    
    # The straight length is Total Length - 2 * R_outer (height)
    l_straight = total_length - total_height  # 2.5um
    
    layer_wg = (1, 0)
    xs = gf.cross_section.cross_section(width=track_width, layer=layer_wg)

    # =======================================================================
    # 2. Create the Racetrack Body
    # =======================================================================
    p = gf.Path()
    # Path construction starting at (0,0) of the path coordinates
    # 1. Bottom Straight
    p.append(gf.path.straight(length=l_straight))
    # 2. Right Turn (180 deg CCW)
    p.append(gf.path.arc(radius=r_center, angle=180))
    # 3. Top Straight
    p.append(gf.path.straight(length=l_straight))
    # 4. Left Turn (180 deg CCW) -> loops back to start
    p.append(gf.path.arc(radius=r_center, angle=180))
    
    # Extrude the path
    body_shape = gf.path.extrude(p, cross_section=xs)
    
    # Container for body to allow centering
    c_body_container = gf.Component("body_container")
    ref_body = c_body_container << body_shape
    
    # Manually Calculate Center to avoid 'align' attribute errors
    # Path logic:
    # Start: (0,0)
    # End of Bottom Straight: (l_straight, 0)
    # End of Right Arc: (l_straight, 2*r_center) -> Top Y
    # Center X is l_straight / 2
    # Center Y is r_center
    center_offset_x = l_straight / 2.0
    center_offset_y = r_center
    
    # Move body to be centered at (0,0)
    ref_body.move((-center_offset_x, -center_offset_y))

    # =======================================================================
    # 3. Create the "Holes" (Windows)
    # =======================================================================
    c_holes_container = gf.Component("holes_container")
    
    # Hole dimensions
    hole_len = 0.85
    hole_width = 0.4
    gap_between_holes = 0.3
    
    # Calculate positions relative to (0,0)
    # X position: half the gap + half the hole length
    x_pos = (gap_between_holes / 2.0) + (hole_len / 2.0)
    # Y position: The track center is at r_center (which is 1.1um here)
    y_pos = r_center

    hole_rect = gf.components.rectangle(
        size=(hole_len, hole_width), 
        layer=layer_wg, 
        centered=True
    )

    # Place 4 holes (Top-Right, Top-Left, Bottom-Right, Bottom-Left)
    offsets = [
        (x_pos, y_pos),
        (-x_pos, y_pos),
        (x_pos, -y_pos),
        (-x_pos, -y_pos)
    ]

    for dx, dy in offsets:
        h = c_holes_container << hole_rect
        h.move((dx, dy))

    # =======================================================================
    # 4. Boolean Subtraction
    # =======================================================================
    # Subtract holes from the centered body
    final_shape = gf.boolean(
        A=c_body_container,
        B=c_holes_container,
        operation="not",
        layer=layer_wg
    )
    
    c << final_shape
    
    return c

if __name__ == "__main__":
    # Create the device
    device = device_recreated()
    
    # Write the GDS file
    device.write_gds("device_recreated.gds")
    
    # Optional: print confirmation
    print(f"GDS file written: device_recreated.gds. Footprint: {device.size_info}")