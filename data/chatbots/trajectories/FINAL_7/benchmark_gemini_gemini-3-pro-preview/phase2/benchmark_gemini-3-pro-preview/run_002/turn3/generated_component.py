import gdsfactory as gf

@gf.cell
def device_racetrack_heaters():
    c = gf.Component()

    # =======================================================================
    # 1. Dimensions & Global Parameters
    # =======================================================================
    # Device Envelope
    h_device = 3.0
    w_device = 5.5
    
    # --- Outer Ring ---
    w_ring = 0.5
    # Centerline radius derived from total height: (3.0 - 0.5) / 2
    r_ring_center = (h_device - w_ring) / 2.0  # 1.25
    
    # Straight length derived from total width and height
    # Total Width = l_straight + 2 * (Radius + w_ring/2)
    # 5.5 = l_straight + 3.0 => l_straight = 2.5
    l_straight = 2.5
    
    # --- Inner Structures (Arms) ---
    w_pad = 0.6         # Width of the rectangular pad
    w_wire = 0.2        # Width of the heating wire
    gap_center_x = 0.4  # Horizontal gap between left/right pads
    
    # Concentricity Calculation:
    # Outer Ring Inner Edge = r_ring_center - w_ring/2 = 1.0
    # Desired Gap ~ 0.2 -> Wire Outer Edge ~ 0.8
    # Wire Center ~ 0.8 - w_wire/2 = 0.7
    r_inner_center = 0.7
    
    # Length Calculations:
    # Ring straight ends at x = l_straight/2 = 1.25
    # Arm starts at x = gap_center_x/2 = 0.2
    # Available Length = 1.25 - 0.2 = 1.05
    l_pad = 0.65
    l_taper = 0.4
    # 0.65 + 0.4 = 1.05 (Matches geometry perfectly)

    bend_angle = 60

    # =======================================================================
    # 2. Cross Sections
    # =======================================================================
    # Define cross-sections to carry width and layer info.
    # radius_min=0 is essential to avoid "ValueError: min_bend_radius < 10.0"
    
    xs_ring = gf.cross_section.cross_section(
        width=w_ring,
        layer=(1, 0),
        radius=r_ring_center,
        radius_min=0.0
    )
    
    xs_pad = gf.cross_section.cross_section(
        width=w_pad,
        layer=(1, 0),
        radius_min=0.0
    )
    
    xs_wire = gf.cross_section.cross_section(
        width=w_wire,
        layer=(1, 0),
        radius=r_inner_center,
        radius_min=0.0
    )

    # =======================================================================
    # 3. Build Outer Ring
    # =======================================================================
    # Top Straight
    wg_top = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    wg_top.move((-l_straight/2, r_ring_center))
    
    # Bottom Straight
    wg_bot = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    wg_bot.move((-l_straight/2, -r_ring_center))
    
    # Right Bend (Clockwise 180 deg)
    bend_r = c << gf.components.bend_circular(
        radius=r_ring_center, angle=-180, cross_section=xs_ring
    )
    bend_r.connect("o1", wg_top.ports["o2"])
    
    # Left Bend (Clockwise 180 deg)
    bend_l = c << gf.components.bend_circular(
        radius=r_ring_center, angle=-180, cross_section=xs_ring
    )
    bend_l.connect("o1", wg_bot.ports["o1"])

    # =======================================================================
    # 4. Build Inner Arms
    # =======================================================================
    def create_arm():
        arm = gf.Component()
        
        # 1. Pad (Thick Block)
        # Use cross_section instead of raw width/layer
        p = arm << gf.components.straight(
            length=l_pad, 
            cross_section=xs_pad
        )
        
        # 2. Taper (Transition)
        # Pass cross_section to define the layer, but override widths
        t = arm << gf.components.taper(
            length=l_taper, 
            width1=w_pad, 
            width2=w_wire, 
            cross_section=xs_pad
        )
        t.connect("o1", p.ports["o2"])
        
        # 3. Bend (Concentric Arc)
        b = arm << gf.components.bend_circular(
            radius=r_inner_center, 
            angle=-bend_angle, 
            cross_section=xs_wire
        )
        b.connect("o1", t.ports["o2"])
        
        arm.add_port("o1", port=p.ports["o1"])
        return arm

    # Instantiate the template
    arm_template = create_arm()
    
    x_off = gap_center_x / 2.0
    y_off = r_inner_center
    
    # -- Top Right --
    tr = c << arm_template
    tr.move((x_off, y_off))
    
    # -- Bottom Right -- 
    # Mirror Top-Right across X-axis
    br = c << arm_template
    br.mirror(p1=(0,0), p2=(1,0))
    br.move((x_off, -y_off))
    
    # -- Top Left --
    # Mirror Top-Right across Y-axis
    tl = c << arm_template
    tl.mirror(p1=(0,0), p2=(0,1))
    tl.move((-x_off, y_off))
    
    # -- Bottom Left --
    # Rotate Top-Right 180 degrees
    bl = c << arm_template
    bl.rotate(180)
    bl.move((-x_off, -y_off))

    return c

if __name__ == "__main__":
    device = device_racetrack_heaters()
    device.write_gds("racetrack_heaters.gds")
    device.show()