import gdsfactory as gf
import gdsfactory.components as gc

@gf.cell
def racetrack_with_heaters_fixed():
    c = gf.Component()
    
    # =========================================================================
    # 1. Dimensions & Layers
    # =========================================================================
    # Using layer (1, 0) for all geometry as per the binary image style
    layer_wg = (1, 0)
    
    # Constraints derived from footprint (3um x 5.5um)
    device_height = 3.0
    device_length = 5.5
    wg_width = 0.5
    
    # Calculate geometric parameters
    # Outer radius = 1.5. Center radius = 1.5 - 0.25 = 1.25.
    r_center = (device_height - wg_width) / 2  # 1.25
    l_straight = device_length - device_height # 5.5 - 3.0 = 2.5
    
    # Define Cross Sections
    # CRITICAL FIX: Set 'radius' here to prevent radius_min validation errors
    xs_ring = gf.cross_section.cross_section(
        width=wg_width, 
        layer=layer_wg, 
        radius=r_center
    )
    
    # Trace for the inner heater
    trace_width = 0.15
    xs_trace = gf.cross_section.cross_section(width=trace_width, layer=layer_wg)

    # =========================================================================
    # 2. Outer Racetrack Ring
    # =========================================================================
    straight_wg = gc.straight(length=l_straight, cross_section=xs_ring)
    bend_wg = gc.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    
    # Add references
    s_top = c << straight_wg
    s_bot = c << straight_wg
    b_left = c << bend_wg
    b_right = c << bend_wg
    
    # Position and Connect Loop
    # Center the bottom straight at y = -radius
    s_bot.movex(-l_straight/2)
    s_bot.movey(-r_center)
    
    # Connect counter-clockwise
    b_right.connect("o2", s_bot.ports["o2"])
    s_top.connect("o2", b_right.ports["o1"])
    b_left.connect("o1", s_top.ports["o1"])

    # =========================================================================
    # 3. Inner Heater Arms
    # =========================================================================
    # Define one arm consisting of a trace and two pads
    y_arm_offset = 0.6
    pad_len = 0.65
    pad_width = 0.4
    gap_between_pads = 0.2
    arm_core_len = (pad_len * 2) + gap_between_pads
    
    def make_arm():
        arm = gf.Component()
        # Central trace
        t = arm << gc.straight(length=arm_core_len, cross_section=xs_trace)
        # Pads
        pad = gc.rectangle(size=(pad_len, pad_width), layer=layer_wg, centered=True)
        
        p1 = arm << pad
        p1.move((pad_len/2, 0)) # Center first pad relative to trace start
        
        p2 = arm << pad
        p2.move((arm_core_len - pad_len/2, 0)) # Center second pad relative to trace end
        
        # Expose ports
        arm.add_port("o1", port=t.ports["o1"])
        arm.add_port("o2", port=t.ports["o2"])
        return arm

    arm_comp = make_arm()
    
    # Place Top and Bottom Arms
    arm_top = c << arm_comp
    arm_top.move((-arm_core_len/2, y_arm_offset))
    
    arm_bot = c << arm_comp
    arm_bot.move((-arm_core_len/2, -y_arm_offset))

    # =========================================================================
    # 4. Hubs and Connections (S-Bends)
    # =========================================================================
    # Create the rectangular merge points inside the bends
    hub_w = 0.6
    hub_h = 0.4
    hub = gc.rectangle(size=(hub_w, hub_h), layer=layer_wg, centered=True)
    
    # Calculate Hub Position
    # Sits approximately centered in the gap between the straight section and the bend edge
    x_hub_center = (l_straight/2) + 0.5 
    
    h_right = c << hub
    h_right.move((x_hub_center, 0))
    
    h_left = c << hub
    h_left.move((-x_hub_center, 0))
    
    # Calculate Geometry for S-Bends
    # Horizontal distance from Arm end to Hub edge
    x_arm_end = arm_core_len / 2
    x_hub_edge_inner = x_hub_center - (hub_w / 2)
    dx = x_hub_edge_inner - x_arm_end # Positive distance
    
    # RIGHT SIDE CONNECTIONS
    # Top Right: Go down from y=0.6 to y=0
    sbend_down = gc.bend_s(size=(dx, -y_arm_offset), cross_section=xs_trace)
    tr = c << sbend_down
    tr.connect("o1", arm_top.ports["o2"])
    
    # Bottom Right: Go up from y=-0.6 to y=0
    sbend_up = gc.bend_s(size=(dx, y_arm_offset), cross_section=xs_trace)
    br = c << sbend_up
    br.connect("o1", arm_bot.ports["o2"])
    
    # LEFT SIDE CONNECTIONS
    # Note: Connecting to "o1" (West facing) rotates the component 180 degrees.
    # A local vector (x, y) becomes global (-x, -y).
    
    # Top Left: Needs global (-dx, -0.6). Local must be (dx, 0.6).
    sbend_tl = gc.bend_s(size=(dx, y_arm_offset), cross_section=xs_trace)
    tl = c << sbend_tl
    tl.connect("o1", arm_top.ports["o1"])
    
    # Bottom Left: Needs global (-dx, +0.6). Local must be (dx, -0.6).
    sbend_bl = gc.bend_s(size=(dx, -y_arm_offset), cross_section=xs_trace)
    bl = c << sbend_bl
    bl.connect("o1", arm_bot.ports["o1"])
    
    return c

if __name__ == "__main__":
    device = racetrack_with_heaters_fixed()
    device.show()
    device.write_gds("racetrack_mzi_fixed.gds")