import gdsfactory as gf

@gf.cell
def recreate_racetrack_final():
    """
    Reconstructs the racetrack device with two internal lanes and side hubs.
    Footprint target: 5.5um (width) x 3.0um (height).
    """
    c = gf.Component("racetrack_device")
    layer = (1, 0)

    # 1. GEOMETRY PARAMETERS (Strictly adhering to [3.0, 5.5] footprint)
    total_w = 5.5
    total_h = 3.0
    ring_w = 0.58  # Thicker ring to match the visual weight of the original
    
    # Outer radius is half of the total height
    r_out = total_h / 2 # 1.5um
    # Straight length is total width minus two radii
    l_straight = total_w - 2 * r_out # 2.5um
    # Path radius for the center-line extrusion
    r_path = r_out - ring_w / 2

    # Cross section for the main ring
    xs = gf.cross_section.cross_section(
        width=ring_w, 
        layer=layer, 
        radius_min=0.1 # Essential for small bends
    )
    
    # 2. OUTER RACETRACK RING
    # Constructed from segments to ensure perfect port alignment
    bot = c << gf.components.straight(length=l_straight, cross_section=xs)
    bot.move((-l_straight / 2, -r_path))
    
    right_arc = c << gf.components.bend_circular(radius=r_path, angle=180, cross_section=xs)
    right_arc.connect("o1", bot.ports["o2"])
    
    top = c << gf.components.straight(length=l_straight, cross_section=xs)
    top.connect("o1", right_arc.ports["o2"])
    
    left_arc = c << gf.components.bend_circular(radius=r_path, angle=180, cross_section=xs)
    left_arc.connect("o1", top.ports["o2"])

    # 3. INTERNAL STRUCTURE
    # Side Hubs: Blocks attached to the apex of the inner curves
    hub_w = 0.65
    hub_h = 1.0
    # Position hubs out into the arc area (x ~ 1.85um from center)
    hub_x_pos = 1.85
    
    hub_l = c << gf.components.rectangle(size=(hub_w, hub_h), layer=layer, centered=True)
    hub_l.movex(-hub_x_pos)
    hub_r = c << gf.components.rectangle(size=(hub_w, hub_h), layer=layer, centered=True)
    hub_r.movex(hub_x_pos)

    # Lane details
    pad_w = 1.1    # Width of individual pads
    pad_h = 0.52   # Height of pads
    lane_y = 0.75  # Vertical offset of lane center
    arm_w = 0.38   # Thickness of the connecting arms
    pad_gap = 0.12 # Central vertical gap between pads
    
    def add_internal_lane(y_sign):
        y = y_sign * lane_y
        
        # A. Central Pads (Two per lane)
        p1 = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
        p1.move((-pad_w/2 - pad_gap/2, y))
        p2 = c << gf.components.rectangle(size=(pad_w, pad_h), layer=layer, centered=True)
        p2.move((pad_w/2 + pad_gap/2, y))
        
        # B. Angled arms connecting Hubs to Lanes
        # Left Arm
        pts_l = [(-hub_x_pos, 0), (-1.25, y)]
        c << gf.path.extrude(gf.Path(pts_l), cross_section=gf.cross_section.cross_section(width=arm_w, layer=layer))
        
        # Right Arm
        pts_r = [(hub_x_pos, 0), (1.25, y)]
        c << gf.path.extrude(gf.Path(pts_r), cross_section=gf.cross_section.cross_section(width=arm_w, layer=layer))
        
        # C. Bridge segments to overlap and smooth the junction to pads
        bridge_l = c << gf.components.rectangle(size=(0.4, arm_w), layer=layer, centered=True)
        bridge_l.move((-1.1, y))
        bridge_r = c << gf.components.rectangle(size=(0.4, arm_w), layer=layer, centered=True)
        bridge_r.move((1.1, y))

    add_internal_lane(1)  # Top lane
    add_internal_lane(-1) # Bottom lane

    # 4. FINAL BOOLEAN UNION
    # This merges all overlapping components into a single clean polygon
    final_c = gf.Component("final_geometry")
    unified = gf.boolean(A=c, B=c, operation="or", layer=layer)
    final_c << unified
    
    return final_c

if __name__ == "__main__":
    # Create the device
    device = recreate_racetrack_final()
    
    # To view: device.show()
    # To save:
    device.write_gds("racetrack_v4_refined.gds")