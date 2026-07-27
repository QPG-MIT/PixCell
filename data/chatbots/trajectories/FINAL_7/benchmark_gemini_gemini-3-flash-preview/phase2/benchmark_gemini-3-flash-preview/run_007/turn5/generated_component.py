import gdsfactory as gf

@gf.cell
def recreate_racetrack_v5():
    """
    Refined racetrack device with two internal lanes and side hubs.
    Footprint target: 5.5um (width) x 3.0um (height).
    """
    c = gf.Component("racetrack_v5")
    layer = (1, 0)

    # 1. GEOMETRY PARAMETERS
    total_w = 5.5
    total_h = 3.0
    ring_w = 0.58  # Thickness of the racetrack border
    
    # Dimensions for stadium shape (l_straight + 2 * radius = total_width)
    r_outer = total_h / 2 # 1.5um
    l_straight = total_w - 2 * r_outer # 2.5um

    # 2. MAIN RACETRACK RING
    # We build the ring by subtracting a smaller stadium from a larger one
    def make_stadium(w, h, lay):
        s = gf.Component()
        rad = h / 2
        ls = w - 2 * rad
        # Central rectangle
        s << gf.components.rectangle(size=(ls, h), layer=lay, centered=True)
        # Circular end caps
        cap = gf.components.circle(radius=rad, layer=lay)
        cl = s << cap
        cl.movex(-ls/2)
        cr = s << cap
        cr.movex(ls/2)
        return s

    outer_ref = make_stadium(total_w, total_h, layer)
    inner_ref = make_stadium(total_w - 2*ring_w, total_h - 2*ring_w, layer)
    
    # Boolean subtraction to create the hollow ring
    ring = gf.boolean(A=outer_ref, B=inner_ref, operation="not", layer=layer)
    c << ring

    # 3. INTERNAL HUBS
    # Vertical bars on the left and right that the lanes connect to
    hub_w = 0.6
    hub_h = 1.15
    hub_x_pos = 1.95 # Positioned to overlap with the inner curve
    
    hub_l = c << gf.components.rectangle(size=(hub_w, hub_h), layer=layer, centered=True)
    hub_l.movex(-hub_x_pos)
    hub_r = c << gf.components.rectangle(size=(hub_w, hub_h), layer=layer, centered=True)
    hub_r.movex(hub_x_pos)

    # 4. INTERNAL LANES & PADS
    pad_w = 1.1
    pad_h = 0.5
    lane_y_offset = 0.72  # Vertical position of top/bottom lanes
    pad_gap_center = 0.12 # Slit between left and right pads in a lane
    arm_w = 0.38
    
    # Create the 4 central pads
    # Top Lane
    p_tl = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    p_tl.move((-pad_w/2 - pad_gap_center/2, lane_y_offset))
    p_tr = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    p_tr.move((pad_w/2 + pad_gap_center/2, lane_y_offset))
    
    # Bottom Lane
    p_bl = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    p_bl.move((-pad_w/2 - pad_gap_center/2, -lane_y_offset))
    p_br = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
    p_br.move((pad_w/2 + pad_gap_center/2, -lane_y_offset))

    # 5. CONNECTING ARMS
    # Function to create an arm with a horizontal segment then an angled elbow
    def add_elbow_arm(start_x, start_y, end_x, end_y, side_sign):
        # start is pad edge, end is hub face
        # We add a waypoint to create the elbow effect
        mid_x = start_x + side_sign * (abs(end_x - start_x) * 0.4)
        pts = [(start_x, start_y), (mid_x, start_y), (end_x, end_y)]
        path = gf.Path(pts)
        c << gf.path.extrude(path, cross_section=gf.cross_section.cross_section(width=arm_w, layer=layer))

    # Calculate connection points
    hub_face_x = hub_x_pos - hub_w/2
    hub_conn_y = 0.3  # Height on the hub where the angled arms meet
    pad_edge_x = pad_w + pad_gap_center/2

    # Connect Left Hub
    add_elbow_arm(-pad_edge_x, lane_y_offset, -hub_face_x, hub_conn_y, -1)
    add_elbow_arm(-pad_edge_x, -lane_y_offset, -hub_face_x, -hub_conn_y, -1)
    
    # Connect Right Hub
    add_elbow_arm(pad_edge_x, lane_y_offset, hub_face_x, hub_conn_y, 1)
    add_elbow_arm(pad_edge_x, -lane_y_offset, hub_face_x, -hub_conn_y, 1)

    # 6. FINAL BOOLEAN UNION
    # Merges all pieces into a single clean polygon
    final_c = gf.Component("final_device")
    unified = gf.boolean(A=c, B=c, operation="or", layer=layer)
    final_c << unified
    
    return final_c

if __name__ == "__main__":
    device = recreate_racetrack_v5()
    device.write_gds("racetrack_v5.gds")