import gdsfactory as gf

@gf.cell
def mzi_device_recreated():
    c = gf.Component("final_device")
    layer = (1, 0)
    
    # 1. DIMENSIONS & MATH
    # Total footprint: Width = 5.5, Height = 3.0
    total_w = 5.5
    total_h = 3.0
    ring_width = 0.5  # Thickness of the outer frame
    
    # Centerline radius calculation:
    # To have a total height of 3.0: 2 * R_centerline + ring_width = 3.0
    # 2 * Rc + 0.5 = 3.0  => 2 * Rc = 2.5 => Rc = 1.25
    r_center = 1.25
    
    # Straight segment calculation:
    # To have a total width of 5.5: L_straight + 2 * R_outer = 5.5
    # R_outer = Rc + ring_width/2 = 1.25 + 0.25 = 1.5
    # L_straight + 2 * 1.5 = 5.5 => L_straight + 3.0 = 5.5 => L_straight = 2.5
    l_straight = 2.5

    # 2. CROSS SECTION
    # Explicitly set radius=r_center to override the default 10um minimum radius limit
    xs = gf.cross_section.cross_section(width=ring_width, layer=layer, radius=r_center)

    # 3. OUTER RACETRACK FRAME
    # Build from components to ensure perfect port alignment
    rt = gf.Component("racetrack")
    s1 = rt << gf.components.straight(length=l_straight, cross_section=xs)
    b1 = rt << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs)
    s2 = rt << gf.components.straight(length=l_straight, cross_section=xs)
    b2 = rt << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs)
    
    # Chain connections using ports
    b1.connect("o1", s1.ports["o2"])
    s2.connect("o1", b1.ports["o2"])
    b2.connect("o1", s2.ports["o2"])
    s1.connect("o1", b2.ports["o2"]) # Closes the loop
    
    # Move the racetrack to be centered at (0,0)
    rt_ref = c << rt
    rt_ref.move((-l_straight / 2, -r_center))

    # 4. INNER MZI STRUCTURE
    mzi = gf.Component("mzi_inner")
    
    # Side feed blocks
    block_w, block_h = 0.6, 0.9
    block_x_offset = 2.2 # Position near the start of the bends
    
    lb = mzi << gf.components.rectangle(size=(block_w, block_h), layer=layer, centered=True)
    lb.movex(-block_x_offset)
    rb = mzi << gf.components.rectangle(size=(block_w, block_h), layer=layer, centered=True)
    rb.movex(block_x_offset)
    
    # Arm waveguides
    arm_width = 0.18
    arm_y_offset = 0.65 # Vertical separation of the arms
    transition_length = 0.5
    
    x_start = -block_x_offset + block_w/2
    x_end = block_x_offset - block_w/2
    
    for y_sign in [1, -1]:
        y_pos = y_sign * arm_y_offset
        # Define path from left block to right block
        pts = [
            (x_start, 0),
            (x_start + transition_length, y_pos),
            (x_end - transition_length, y_pos),
            (x_end, 0)
        ]
        mzi << gf.path.extrude(gf.Path(pts), width=arm_width, layer=layer)
        
        # Dual heater/tuning blocks per arm
        h_w, h_h = 0.85, 0.45
        h_gap = 0.12 # Small gap between the two blocks
        
        h1 = mzi << gf.components.rectangle(size=(h_w, h_h), layer=layer, centered=True)
        h1.move((-h_w/2 - h_gap/2, y_pos))
        
        h2 = mzi << gf.components.rectangle(size=(h_w, h_h), layer=layer, centered=True)
        h2.move((h_w/2 + h_gap/2, y_pos))

    # Add MZI to main component
    c << mzi

    return c

if __name__ == "__main__":
    # Create the component
    device = mzi_device_recreated()
    
    # Display the result
    device.show()
    
    # Export for verification
    device.write_gds("mzi_racetrack_fixed.gds")