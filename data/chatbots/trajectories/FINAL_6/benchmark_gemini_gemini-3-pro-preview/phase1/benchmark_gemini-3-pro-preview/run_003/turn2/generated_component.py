import gdsfactory as gf

@gf.cell
def device_cross_flower_v2():
    c = gf.Component()

    # --- Dimensions ---
    # Total footprint constraint: 4.7um x 4.7um
    # Radius: 2.35um
    
    # We split the arm length into 3 segments: 
    # 1. Inner Petal (Expanding)
    # 2. Outer Petal (Contracting)
    # 3. Tip (Straight)
    # Lengths estimated to sum to 2.35um
    l_expand = 0.9 
    l_contract = 0.9
    l_tip = 0.55
    
    # Widths derived from visual proportions
    w_center = 0.35   # Finite width at center to ensure solid overlap
    w_max = 1.0       # Maximum width of the bulbous petal
    w_tip = 0.2       # Narrow width for the tip
    
    layer_wg = (1, 0)

    # --- Cross Sections ---
    xs_center = gf.cross_section.cross_section(width=w_center, layer=layer_wg)
    xs_max = gf.cross_section.cross_section(width=w_max, layer=layer_wg)
    xs_tip = gf.cross_section.cross_section(width=w_tip, layer=layer_wg)

    # --- Constructing One Arm ---
    arm = gf.Component()

    # 1. Expansion Part (Center -> Max Width)
    # 'sine' transition creates a smooth, curved expansion (slope is 0 at ends)
    t1 = gf.path.transition(xs_center, xs_max, width_type='sine')
    p1 = gf.path.straight(length=l_expand)
    part1 = arm << gf.path.extrude_transition(p1, t1)

    # 2. Contraction Part (Max Width -> Tip Width)
    t2 = gf.path.transition(xs_max, xs_tip, width_type='sine')
    p2 = gf.path.straight(length=l_contract)
    part2 = arm << gf.path.extrude_transition(p2, t2)
    
    # Connect Part 2 to Part 1
    part2.connect("o1", part1.ports["o2"])

    # 3. Straight Tip
    part3 = arm << gf.components.straight(length=l_tip, cross_section=xs_tip)
    
    # Connect Tip to Part 2
    part3.connect("o1", part2.ports["o2"])
    
    # Define the arm's anchor port (at the start of part1)
    arm.add_port("o1", port=part1.ports["o1"])
    arm.add_port("o2", port=part3.ports["o2"])

    # --- Final Assembly ---
    # Place 4 arms rotated by 90 degrees
    for i, angle in enumerate([0, 90, 180, 270]):
        ref = c << arm
        ref.rotate(angle)
        # By default, rotation happens around (0,0). 
        # Since the arm starts at (0,0), this arranges them radially.
        
        c.add_port(f"o{i+1}", port=ref.ports["o2"])

    return c

if __name__ == "__main__":
    device = device_cross_flower_v2()
    device.write_gds("device_cross_flower_v2.gds")
    
    # Verify dimensions
    print(f"Device Footprint: {device.size_info.width:.2f} um x {device.size_info.height:.2f} um")