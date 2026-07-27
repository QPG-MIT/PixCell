import gdsfactory as gf

@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component("directional_coupler")
    
    # Define the cross-section
    width = 0.5
    layer = (1, 0)
    
    # Set `radius=0.1` to lower the minimum bend radius threshold, 
    # preventing ValueError for the relatively tight S-bends.
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius=0.1)
    
    # Calculate geometric parameters to hit [18, 3] footprint exactly
    # Total Length = 18 -> 2 * dx + length = 18
    dx = 5.0
    length = 8.0 
    
    # Total Height = 3 -> gap + 2*width + 2*dy = 3.0
    # Center positions: 0.2 gap + 1.0 (2*width) + 2*0.9 (2*dy) = 3.0
    gap = 0.2
    dy = 0.9
    y_offset = (gap / 2) + (width / 2) # Center position of the inner straight sections (+/- 0.35)
    
    # 1. Create the central straight coupling sections
    straight_top = c << gf.components.straight(length=length, cross_section=xs)
    straight_bot = c << gf.components.straight(length=length, cross_section=xs)
    
    # Move them to establish starting positions (connect() will ultimately snap the ends)
    straight_top.move((-length / 2, y_offset))
    straight_bot.move((-length / 2, -y_offset))
    
    # 2. Create the S-bends to route ports in/out
    # Top goes from outer y (1.25) to inner y (0.35), so dy is negative when connecting backwards
    s_in_top = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    s_out_top = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # Bottom goes from outer y (-1.25) to inner y (-0.35), so dy is positive when connecting backwards
    s_in_bot = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    s_out_bot = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    
    # 3. Connect the S-bends to the central straight waveguides
    s_in_top.connect("o2", straight_top.ports["o1"])
    s_out_top.connect("o1", straight_top.ports["o2"])
    
    s_in_bot.connect("o2", straight_bot.ports["o1"])
    s_out_bot.connect("o1", straight_bot.ports["o2"])
    
    # 4. Add external ports for the overall component
    c.add_port("o1", port=s_in_top.ports["o1"])
    c.add_port("o2", port=s_in_bot.ports["o1"])
    c.add_port("o3", port=s_out_top.ports["o2"])
    c.add_port("o4", port=s_out_bot.ports["o2"])
    
    return c

# Generate the component and save to GDS
if __name__ == "__main__":
    device = directional_coupler()
    # Write the GDS file instead of showing it
    device.write_gds("directional_coupler.gds")