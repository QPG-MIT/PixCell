import gdsfactory as gf

@gf.cell
def recreate_racetrack_final():
    """
    Reconstructs the device with two internal lanes and side hubs.
    Footprint: 5.5um x 3.0um.
    Fixed: radius_min constraint to allow small bends.
    """
    c = gf.Component("racetrack_device")
    layer = (1, 0)

    # 1. PARAMETERS based on [3.0, 5.5] footprint
    total_w = 5.5
    total_h = 3.0
    ring_w = 0.52  
    
    # R_out = 1.5 (half of 3.0 height)
    # L_straight = 5.5 - (2 * 1.5) = 2.5
    r_out = total_h / 2
    l_straight = total_w - 2 * r_out
    r_path = r_out - ring_w / 2

    # 2. CROSS SECTION FIX
    # Explicitly set radius_min to 0.1 to override the default 10.0 limit
    xs = gf.cross_section.cross_section(
        width=ring_w, 
        layer=layer, 
        radius_min=0.1
    )
    
    # 3. OUTER RACETRACK RING
    # Build using components to ensure exact connectivity
    bot = c << gf.components.straight(length=l_straight, cross_section=xs)
    bot.move((-l_straight / 2, -r_path))
    
    right_arc = c << gf.components.bend_circular(radius=r_path, angle=180, cross_section=xs)
    right_arc.connect("o1", bot.ports["o2"])
    
    top = c << gf.components.straight(length=l_straight, cross_section=xs)
    top.connect("o1", right_arc.ports["o2"])
    
    left_arc = c << gf.components.bend_circular(radius=r_path, angle=180, cross_section=xs)
    left_arc.connect("o1", top.ports["o2"])

    # 4. INTERNAL STRUCTURE
    # Side Hubs (the thick connection points on the inner curves)
    hub_w = 0.55
    hub_h = 1.1
    hub_x_pos = l_straight / 2 + 0.1
    
    hub_l = c << gf.components.rectangle(size=(hub_w, hub_h), layer=layer, centered=True)
    hub_l.movex(-hub_x_pos)
    hub_r = c << gf.components.rectangle(size=(hub_w, hub_h), layer=layer, centered=True)
    hub_r.movex(hub_x_pos)

    # Internal Lane Function
    pad_w = 0.85
    pad_h = 0.45
    lane_y_offset = 0.7 
    arm_w = 0.3 # Thickness of the angled segments
    
    def add_internal_lane(y_sign):
        y = y_sign * lane_y_offset
        
        # Angled Arms from Hub to lane area
        pts_l = [(-hub_x_pos, 0), (-1.2, y)]
        c << gf.path.extrude(gf.Path(pts_l), cross_section=gf.cross_section.cross_section(width=arm_w, layer=layer))
        
        pts_r = [(hub_x_pos, 0), (1.2, y)]
        c << gf.path.extrude(gf.Path(pts_r), cross_section=gf.cross_section.cross_section(width=arm_w, layer=layer))
        
        # Two central pads per lane
        gap = 0.1
        p1 = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
        p1.move((-pad_w/2 - gap/2, y))
        p2 = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
        p2.move((pad_w/2 + gap/2, y))
        
        # Connector segments between pads and arms
        conn_l = c << gf.components.rectangle(size=(0.5, arm_w), layer=layer, centered=True)
        conn_l.move((-1.2, y))
        conn_r = c << gf.components.rectangle(size=(0.5, arm_w), layer=layer, centered=True)
        conn_r.move((1.2, y))

    add_internal_lane(1)  # Top
    add_internal_lane(-1) # Bottom

    # 5. FINAL BOOLEAN MERGE
    final_c = gf.Component("final_geometry")
    unified = gf.boolean(A=c, B=c, operation="or", layer=layer)
    final_c << unified
    
    return final_c

if __name__ == "__main__":
    device = recreate_racetrack_final()
    device.show()
    device.write_gds("racetrack_v3_fixed.gds")