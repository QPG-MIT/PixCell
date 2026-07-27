import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Parametric directional coupler built from primitives to exactly 
    match a [120, 4] footprint.
    """
    c = gf.Component("directional_coupler")
    
    # 1. Define standard waveguide cross-section
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Footprint Constraints & Mathematical Breakdown
    # Total length = 120 um
    # Total height = 4 um 
    # Max Y = 2.0, Min Y = -2.0 -> Input port centers are at Y = +/- 1.75
    dy_pitch = 4.0 - wg_width  # 3.5 um (distance between top and bottom port centers)
    
    # Coupling gap and center calculation
    gap = 0.2
    coupler_y = (gap / 2) + (wg_width / 2)  # Y-center of the arm in the coupling region (0.35)
    
    # S-bend vertical shift
    shift_y = (dy_pitch / 2) - coupler_y  # Distance s-bend needs to traverse vertically (1.4)
    
    # Horizontal length partitioning (sums to 120: 20 + 20 + 40 + 20 + 20 = 120)
    in_len = 20.0     # Input straight length
    dx = 20.0         # S-bend horizontal length
    mid_len = 40.0    # Coupling region straight length
    
    # 3. Create Primitive Instances
    straight_in_out = gf.components.straight(length=in_len, cross_section=xs)
    straight_mid = gf.components.straight(length=mid_len, cross_section=xs)
    
    # S-bends for transitions (positive dy routes UP, negative dy routes DOWN)
    bend_s_down = gf.components.bend_s(size=(dx, -shift_y), cross_section=xs)
    bend_s_up = gf.components.bend_s(size=(dx, shift_y), cross_section=xs)

    # ==========================================
    # 4. Assemble Top Arm
    # ==========================================
    st_in_t = c << straight_in_out
    sbend_in_t = c << bend_s_down
    st_mid_t = c << straight_mid
    sbend_out_t = c << bend_s_up
    st_out_t = c << straight_in_out

    # Position start and chain connect
    st_in_t.move((0, dy_pitch / 2))
    sbend_in_t.connect("o1", st_in_t.ports["o2"])
    st_mid_t.connect("o1", sbend_in_t.ports["o2"])
    sbend_out_t.connect("o1", st_mid_t.ports["o2"])
    st_out_t.connect("o1", sbend_out_t.ports["o2"])

    # ==========================================
    # 5. Assemble Bottom Arm
    # ==========================================
    st_in_b = c << straight_in_out
    sbend_in_b = c << bend_s_up
    st_mid_b = c << straight_mid
    sbend_out_b = c << bend_s_down
    st_out_b = c << straight_in_out

    # Position start and chain connect
    st_in_b.move((0, -dy_pitch / 2))
    sbend_in_b.connect("o1", st_in_b.ports["o2"])
    st_mid_b.connect("o1", sbend_in_b.ports["o2"])
    sbend_out_b.connect("o1", st_mid_b.ports["o2"])
    st_out_b.connect("o1", sbend_out_b.ports["o2"])

    # ==========================================
    # 6. Expose External Ports
    # ==========================================
    c.add_port("o1", port=st_in_t.ports["o1"])
    c.add_port("o2", port=st_in_b.ports["o1"])
    c.add_port("o3", port=st_out_t.ports["o2"])
    c.add_port("o4", port=st_out_b.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate and explicitly save the component to a GDS file
    device = directional_coupler_120x4()
    device.write_gds("directional_coupler_120x4.gds")