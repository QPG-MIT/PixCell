import gdsfactory as gf

@gf.cell
def racetrack_device_fixed():
    """
    Recreates the device geometry with explicit layer parameters for boolean operations.
    Footprint: 5.5um x 3.0um.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # --- 1. Dimensions ---
    total_w = 5.5
    total_h = 3.0
    r_outer = total_h / 2         # 1.5 um
    l_straight = total_w - 2 * r_outer  # 2.5 um
    wall_thickness = 0.45
    r_inner = r_outer - wall_thickness
    
    # --- 2. Stadium Frame Construction ---
    # We create the shapes and then use booleans with the required layer argument
    
    # Outer Stadium
    rect_out = gf.components.rectangle(size=(l_straight, 2 * r_outer), centered=True, layer=layer)
    circ_out = gf.components.circle(radius=r_outer, layer=layer)
    
    # OR the central rectangle with the two ends
    s_out = gf.boolean(rect_out, circ_out.copy().movex(-l_straight/2), operation="or", layer=layer)
    s_out = gf.boolean(s_out, circ_out.copy().movex(l_straight/2), operation="or", layer=layer)
    
    # Inner Stadium
    rect_in = gf.components.rectangle(size=(l_straight, 2 * r_inner), centered=True, layer=layer)
    circ_in = gf.components.circle(radius=r_inner, layer=layer)
    
    s_in = gf.boolean(rect_in, circ_in.copy().movex(-l_straight/2), operation="or", layer=layer)
    s_in = gf.boolean(s_in, circ_in.copy().movex(l_straight/2), operation="or", layer=layer)
    
    # Subtract inner from outer to create the hollow ring
    frame = gf.boolean(s_out, s_in, operation="not", layer=layer)
    
    # Handle the case where boolean might return a list of polygons or a Component
    if isinstance(frame, list):
        for polygon in frame:
            c.add_polygon(polygon, layer=layer)
    else:
        c << frame

    # --- 3. Internal Branch Structure ---
    # Central vertical junctions on the left and right inner walls
    j_w, j_h = 0.4, 0.9
    j_left = c << gf.components.rectangle(size=(j_w, j_h), centered=True, layer=layer)
    j_left.movex(-l_straight/2 + j_w/2)
    
    j_right = c << gf.components.rectangle(size=(j_w, j_h), centered=True, layer=layer)
    j_right.movex(l_straight/2 - j_w/2)
    
    # Parameters for the branches
    y_offset = 0.65
    arm_w = 0.18
    pad_l, pad_h, pad_gap = 0.7, 0.45, 0.2
    
    for y_sign in [1, -1]:
        # Create angled path from the junction to the horizontal arm level
        # Start at the junction edge, move diagonally, then horizontal, then diagonally back
        pts = [
            (-l_straight/2 + j_w, 0),
            (-l_straight/2 + j_w + 0.4, y_sign * y_offset),
            (l_straight/2 - j_w - 0.4, y_sign * y_offset),
            (l_straight/2 - j_w, 0)
        ]
        path = gf.Path(pts)
        c << gf.path.extrude(path, width=arm_w, layer=layer)
        
        # Add the two distinct rectangular pads on each horizontal arm segment
        p1 = c << gf.components.rectangle(size=(pad_l, pad_h), centered=True, layer=layer)
        p1.move((- (pad_l + pad_gap) / 2, y_sign * y_offset))
        
        p2 = c << gf.components.rectangle(size=(pad_l, pad_h), centered=True, layer=layer)
        p2.move(((pad_l + pad_gap) / 2, y_sign * y_offset))
        
    return c

if __name__ == "__main__":
    device = racetrack_device_fixed()
    # Save the file
    device.write_gds("recreated_device_final.gds")
    print("Device generated successfully.")
    # device.show() # Uncomment to view in KLayout