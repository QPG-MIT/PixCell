import gdsfactory as gf

@gf.cell
def directional_coupler() -> gf.Component:
    """
    Creates a symmetric directional coupler recreating the geometry from the image.
    The device is built parametrically to exactly fit the 120 x 4 um footprint constraint.
    """
    c = gf.Component("directional_coupler")
    
    # 1. Define Cross Section
    # Standard waveguide width for silicon photonics is often 0.5 um
    wg_width = 0.5
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # 2. Footprint Constraints & Derived Parameters
    target_length = 120.0
    target_width = 4.0
    
    # Determine segment lengths based on visual proportions from the reference image
    # (Inputs ~1/12th, Bends ~1/4th, Middle ~1/3rd of total length)
    L_in = 10.0
    L_coupling = 40.0
    L_sbend = (target_length - (2 * L_in) - L_coupling) / 2.0  # 30.0 um
    
    # Determine Y-coordinates to satisfy the 4 um total height
    # The bounding box max y is target_width/2 = 2.0 um.
    # Therefore, the top waveguide's center is at 2.0 - (wg_width / 2)
    y_port_center = (target_width - wg_width) / 2.0  # 1.75 um
    
    # Define coupling gap and middle region offsets
    gap = 0.2
    y_couple_center = (gap + wg_width) / 2.0  # 0.35 um
    
    # Vertical displacement for the S-bends
    dy = y_port_center - y_couple_center  # 1.4 um
    
    # 3. Create Component Primitives
    straight_in = gf.components.straight(length=L_in, cross_section=xs)
    straight_mid = gf.components.straight(length=L_coupling, cross_section=xs)
    
    # S-bends for the top arm (converging down, then diverging up)
    bend_top_in = gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    bend_top_out = gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    
    # S-bends for the bottom arm (converging up, then diverging down)
    bend_bot_in = gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    bend_bot_out = gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    
    # 4. Assemble Top Arm
    t1 = c << straight_in
    t2 = c << bend_top_in
    t3 = c << straight_mid
    t4 = c << bend_top_out
    t5 = c << straight_in
    
    # Position first segment and connect the rest sequentially
    t1.movey(y_port_center)
    t2.connect("o1", t1.ports["o2"])
    t3.connect("o1", t2.ports["o2"])
    t4.connect("o1", t3.ports["o2"])
    t5.connect("o1", t4.ports["o2"])
    
    # 5. Assemble Bottom Arm
    b1 = c << straight_in
    b2 = c << bend_bot_in
    b3 = c << straight_mid
    b4 = c << bend_bot_out
    b5 = c << straight_in
    
    # Position first segment and connect the rest sequentially
    b1.movey(-y_port_center)
    b2.connect("o1", b1.ports["o2"])
    b3.connect("o1", b2.ports["o2"])
    b4.connect("o1", b3.ports["o2"])
    b5.connect("o1", b4.ports["o2"])
    
    # 6. Expose External Ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t5.ports["o2"])
    c.add_port("o4", port=b5.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Generate the component and write it to a GDS file
    coupler = directional_coupler()
    coupler.write_gds("directional_coupler.gds")