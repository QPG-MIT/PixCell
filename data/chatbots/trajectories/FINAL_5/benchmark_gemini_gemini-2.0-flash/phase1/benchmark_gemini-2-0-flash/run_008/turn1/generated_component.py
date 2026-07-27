import gdsfactory as gf

@gf.cell
def create_strange_device():
    c = gf.Component("strange_device")

    # Parameters
    wg_width = 0.5  # Estimate based on image
    wg_separation = 1.0 # Estimate based on image
    rib_length = 10.0 # Assume length of rib waveguide sections
    bend_radius = 10.0 # Estimate bend radius from image.  Match cross_section.radius_min
    straight_length = 5.0 #straight section after bend
    gap = 0.1
    num_bars = 30 # Estimate number of bars
    bar_width = 0.1
    bar_sep = 0.1
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius=bend_radius) #radius needs to match bend radius

    # Top Waveguide Branch
    # Create top waveguide
    top_straight = gf.components.straight(length=straight_length, cross_section=xs)
    top_bend = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    top_straight_bar = gf.components.straight(length=num_bars*(bar_width+bar_sep), cross_section=xs)
    
    t_s_b = c << top_straight_bar
    t_s = c << top_straight
    t_b = c << top_bend

    t_s_b.connect("o1", t_s.ports["o2"])
    t_s.connect("o1", t_b.ports["o2"])


    top_straight_end = c << gf.components.straight(length=straight_length, cross_section=xs)
    t_b.connect("o1", top_straight_end.ports["o1"])

    c.add_port("top_1", port=t_s_b.ports["o1"])
    c.add_port("top_2", port=top_straight_end.ports["o2"])

    # Bottom Waveguide Branch - mirror of top
    bottom_straight = gf.components.straight(length=straight_length, cross_section=xs)
    bottom_bend = gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs)
    bottom_straight_bar = gf.components.straight(length=num_bars*(bar_width+bar_sep), cross_section=xs)
    
    b_s_b = c << bottom_straight_bar
    b_s = c << bottom_straight
    b_b = c << bottom_bend

    b_s_b.connect("o1", b_s.ports["o2"])
    b_s.connect("o1", b_b.ports["o2"])


    bottom_straight_end = c << gf.components.straight(length=straight_length, cross_section=xs)
    b_b.connect("o1", bottom_straight_end.ports["o1"])

    c.add_port("bottom_1", port=b_s_b.ports["o1"])
    c.add_port("bottom_2", port=bottom_straight_end.ports["o2"])

    #center rib
    center_rib = c << gf.components.straight(length=num_bars*(bar_width+bar_sep), cross_section=xs)

    # Position elements

    # Rotate and move bottom branch to match the shape
    b_s_b.rotate(180)
    bottom_straight_end.rotate(180)
    b_b.rotate(180)
    b_s.rotate(180)

    # Position elements vertically
    t_s_b.movey(wg_separation/2)
    b_s_b.movey(-wg_separation/2)
    center_rib.movey(0)

    return c

# Create the device
strange_device = create_strange_device()

# Print the device
strange_device.show()

# Write to GDS file
strange_device.write_gds("strange_device.gds")