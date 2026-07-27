import gdsfactory as gf

@gf.cell
def recreate_curved_coupler():
    """
    Recreates the curved waveguide geometry from the image.
    Footprint: 18um x 3um.
    """
    c = gf.Component("curved_coupler")
    
    # 1. Define physical constraints
    length = 18.0
    total_height = 3.0
    wg_width = 0.5
    gap_at_center = 0.2
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # 2. Calculate vertical positions for centerlines
    # y_edge is the vertical position at the start and end of the device
    y_edge = (total_height / 2) - (wg_width / 2)  # 1.5 - 0.25 = 1.25um
    
    # y_center is the vertical position at the middle of the device
    y_center = (gap_at_center / 2) + (wg_width / 2) # 0.1 + 0.25 = 0.35um
    
    # The vertical offset (dy) for a half-length S-bend
    dy_top = y_center - y_edge  # -0.9um (downward dip)
    
    # 3. Construct the Top Waveguide
    # First half: descends from y_edge to y_center
    top_s1 = gf.components.bend_s(size=(length/2, dy_top), cross_section=xs)
    # Second half: ascends from y_center back to y_edge
    top_s2 = gf.components.bend_s(size=(length/2, -dy_top), cross_section=xs)
    
    t1 = c << top_s1
    t1.movey(y_edge)
    t2 = c << top_s2
    t2.connect("o1", t1.ports["o2"])
    
    # 4. Construct the Bottom Waveguide (Mirror of the Top)
    # First half: ascends from -y_edge to -y_center
    bot_s1 = gf.components.bend_s(size=(length/2, -dy_top), cross_section=xs)
    # Second half: descends from -y_center back to -y_edge
    bot_s2 = gf.components.bend_s(size=(length/2, dy_top), cross_section=xs)
    
    b1 = c << bot_s1
    b1.movey(-y_edge)
    b2 = c << bot_s2
    b2.connect("o1", b1.ports["o2"])
    
    # Expose ports for connectivity
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t2.ports["o2"])
    c.add_port("o4", port=b2.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_curved_coupler()
    
    # Export to GDS
    device.write_gds("curved_coupler_recreation.gds")
    
    # Display the result
    device.show()