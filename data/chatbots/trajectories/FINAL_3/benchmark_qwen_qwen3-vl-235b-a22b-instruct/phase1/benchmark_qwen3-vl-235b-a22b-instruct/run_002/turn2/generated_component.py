import gdsfactory as gf

@gf.cell
def recreate_s_bend_device():
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Total dimensions from footprint
    total_length = 120.0  # from footprint
    total_width = 4.0     # from footprint
    
    # Waveguide width
    wg_width = 0.5
    
    # Calculate gap between waveguides
    gap = total_width - 2 * wg_width
    
    # For S-bend, we need to specify the size (dx, dy)
    # dx will be the horizontal offset (length of S-bend)
    # dy will be the vertical offset (how far apart the waveguides are in the middle)
    s_bend_length = total_length / 3
    dy = gap + wg_width  # vertical offset between waveguides in middle section
    
    # Create the top waveguide
    top_s_bend_left = c << gf.components.bend_s(size=(s_bend_length, dy), cross_section=xs)
    top_straight = c << gf.components.straight(length=total_length - 2 * s_bend_length, cross_section=xs)
    top_s_bend_right = c << gf.components.bend_s(size=(s_bend_length, dy), cross_section=xs)
    
    # Create the bottom waveguide
    bottom_s_bend_left = c << gf.components.bend_s(size=(s_bend_length, dy), cross_section=xs)
    bottom_straight = c << gf.components.straight(length=total_length - 2 * s_bend_length, cross_section=xs)
    bottom_s_bend_right = c << gf.components.bend_s(size=(s_bend_length, dy), cross_section=xs)
    
    # Connect top waveguide components
    top_straight.move((s_bend_length, 0))
    top_s_bend_right.move((total_length - s_bend_length, 0))
    
    top_s_bend_left.connect("o2", top_straight.ports["o1"])
    top_straight.connect("o2", top_s_bend_right.ports["o1"])
    
    # For bottom waveguide, we need to mirror the S-bends to create the symmetric shape
    bottom_s_bend_left.move((0, -dy))
    bottom_s_bend_left.mirror(p1=(0, 0), p2=(1, 0))  # Mirror horizontally
    
    bottom_straight.move((s_bend_length, -dy))
    bottom_s_bend_right.move((total_length - s_bend_length, -dy))
    bottom_s_bend_right.mirror(p1=(0, 0), p2=(1, 0))  # Mirror horizontally
    
    bottom_s_bend_left.connect("o2", bottom_straight.ports["o1"])
    bottom_straight.connect("o2", bottom_s_bend_right.ports["o1"])
    
    # Add ports for the device
    c.add_port("o1_top", port=top_s_bend_left.ports["o1"])
    c.add_port("o2_top", port=top_s_bend_right.ports["o2"])
    c.add_port("o1_bottom", port=bottom_s_bend_left.ports["o1"])
    c.add_port("o2_bottom", port=bottom_s_bend_right.ports["o2"])
    
    return c

# Create and save the device
device = recreate_s_bend_device()
device.write_gds("recreated_s_bend_device.gds")