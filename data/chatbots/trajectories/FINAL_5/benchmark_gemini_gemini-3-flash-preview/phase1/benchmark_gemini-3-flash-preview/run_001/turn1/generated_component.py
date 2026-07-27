import gdsfactory as gf

@gf.cell
def create_mirrored_hook_device():
    """
    Recreates the device geometry using parametric primitives.
    Fits footprint: 18.24um x 0.7um.
    """
    c = gf.Component("mirrored_hook_device")

    # --- Configuration & Dimensions (all multiples of 0.002 to satisfy DBU constraints) ---
    layer = (1, 0)
    l_total = 18.24
    w_center = 0.08
    w_arm = 0.04
    l_hook_straight = 10.0
    l_taper = 4.0
    gap_inner = 0.06   # Gap between center line and inner arm
    gap_between = 0.12 # Gap between the two arms of the hook
    
    # Define CrossSections (parametrically handles layer and width)
    xs_center = gf.cross_section.cross_section(width=w_center, layer=layer)
    xs_arm = gf.cross_section.cross_section(width=w_arm, layer=layer)

    # 1. Central Straight Waveguide
    center_wg = c << gf.components.straight(length=l_total, cross_section=xs_center)
    center_wg.x = 0  # Center at origin

    # 2. Define the Hook Sub-component
    @gf.cell
    def make_hook():
        h = gf.Component()
        
        # Outer arm starts with a taper (pointy end)
        # width1=0.01 ensures it is an even multiple of DBU (10 nm)
        taper = h << gf.components.taper(length=l_taper, width1=0.01, width2=w_arm, layer=layer)
        
        # Outer straight segment
        s_outer = h << gf.components.straight(length=l_hook_straight, cross_section=xs_arm)
        s_outer.connect("o1", taper.ports["o2"])
        
        # 180-degree bend
        # The spacing between arm centers is gap_between + w_arm
        bend_radius = (gap_between + w_arm) / 2
        bend = h << gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs_arm)
        bend.connect("o1", s_outer.ports["o2"])
        
        # Inner straight segment (the ladder rail)
        s_inner = h << gf.components.straight(length=l_hook_straight, cross_section=xs_arm)
        s_inner.connect("o1", bend.ports["o2"])
        
        # Grating/Ladder section: periodic vertical rungs
        rung_w = 0.02
        rung_h = gap_between + w_arm
        rung_geo = gf.components.rectangle(size=(rung_w, rung_h), layer=layer, centered=True)
        
        num_rungs = 55
        pitch = l_hook_straight / num_rungs
        for i in range(num_rungs):
            r = h << rung_geo
            r.x = s_inner.xmin + (i + 0.5) * pitch
            # Position rungs vertically between the two straight arms
            r.y = s_inner.y + (gap_between + w_arm) / 2
            
        # Curved Tail at the end of the inner arm (curving away from the center)
        tail = h << gf.components.bend_euler(radius=2.0, angle=60, cross_section=xs_arm)
        tail.connect("o1", s_inner.ports["o2"])
        
        return h

    # 3. Placement of Hooks
    # Vertical offset calculation to ensure 0.7um height constraint
    # target_y = center_width/2 + gap_inner + arm_width/2
    v_offset = (w_center / 2) + gap_inner + (w_arm / 2)
    
    # Add Top Hook (Inner arm sits above center line)
    hook_top = c << make_hook()
    radius = (gap_between + w_arm) / 2
    # Move the whole hook so the inner arm (which is at -2*radius relative to taper) 
    # aligns with v_offset
    hook_top.movey(v_offset + 2 * radius)
    hook_top.xmin = -l_total / 2 + 0.5

    # Add Bottom Hook (Mirrored/Rotated)
    hook_bot = c << make_hook()
    hook_bot.rotate(180)
    hook_bot.movey(-(v_offset + 2 * radius))
    hook_bot.xmax = l_total / 2 - 0.5

    return c

if __name__ == "__main__":
    device = create_mirrored_hook_device()
    device.write_gds("mirrored_hook_device.gds")
    
    # Verification
    bbox = device.bbox
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    print(f"Final Footprint: {width:.2f} um x {height:.2f} um")