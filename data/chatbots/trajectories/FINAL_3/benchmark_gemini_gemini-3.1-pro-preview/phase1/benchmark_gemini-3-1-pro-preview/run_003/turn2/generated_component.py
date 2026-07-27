import gdsfactory as gf

@gf.cell
def directional_coupler():
    c = gf.Component()
    
    # 1. Base Parameters & Constraints
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Constraints required to perfectly hit a 120 x 4 footprint bounding box
    L_total = 120.0
    W_total = 4.0
    wg_width = 0.5
    gap = 0.2

    # Derived geometric parameters for vertical alignment
    # y_port is the center Y-coordinate of the outer ports
    y_port = (W_total - wg_width) / 2.0  
    
    # y_mid is the center Y-coordinate of the waveguides in the coupling region
    y_mid = (gap + wg_width) / 2.0       

    # S-bend vertical shift required to connect port level and mid level
    dy_shift = y_port - y_mid

    # 2. Adjusted Geometric Proportions
    # We reduce the length of the S-bends and ports to stretch out the middle section
    L_end = 10.0        # Short straight port extensions
    dx_sbend = 15.0     # Sharper, shorter horizontal transition for the S-bends
    
    # The middle section takes up all remaining length to guarantee exactly 120um
    L_mid = L_total - (2 * L_end) - (2 * dx_sbend) 

    # 3. Instantiate Base Primitives
    str_end = gf.components.straight(length=L_end, cross_section=xs)
    str_mid = gf.components.straight(length=L_mid, cross_section=xs)
    
    # S-bend pointing down and S-bend pointing up
    sbend_down = gf.components.bend_s(size=(dx_sbend, -dy_shift), cross_section=xs)
    sbend_up = gf.components.bend_s(size=(dx_sbend, dy_shift), cross_section=xs)

    # 4. Assemble Components (Top Arm)
    t_end1 = c << str_end
    t_end1.move((0, y_port))

    t_sbend1 = c << sbend_down
    t_sbend1.connect("o1", t_end1.ports["o2"])

    t_mid = c << str_mid
    t_mid.connect("o1", t_sbend1.ports["o2"])

    t_sbend2 = c << sbend_up
    t_sbend2.connect("o1", t_mid.ports["o2"])

    t_end2 = c << str_end
    t_end2.connect("o1", t_sbend2.ports["o2"])

    # 5. Assemble Components (Bottom Arm)
    b_end1 = c << str_end
    b_end1.move((0, -y_port))

    b_sbend1 = c << sbend_up
    b_sbend1.connect("o1", b_end1.ports["o2"])

    b_mid = c << str_mid
    b_mid.connect("o1", b_sbend1.ports["o2"])

    b_sbend2 = c << sbend_down
    b_sbend2.connect("o1", b_mid.ports["o2"])

    b_end2 = c << str_end
    b_end2.connect("o1", b_sbend2.ports["o2"])

    # 6. Export Exterior Ports
    c.add_port("o1", port=t_end1.ports["o1"])
    c.add_port("o2", port=b_end1.ports["o1"])
    c.add_port("o3", port=t_end2.ports["o2"])
    c.add_port("o4", port=b_end2.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the instance and save to a GDS file
    coupler = directional_coupler()
    coupler.write_gds("directional_coupler_adjusted.gds")