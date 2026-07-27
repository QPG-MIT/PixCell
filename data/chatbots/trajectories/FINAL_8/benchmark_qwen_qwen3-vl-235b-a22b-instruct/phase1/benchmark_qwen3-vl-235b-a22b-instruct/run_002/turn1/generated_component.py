import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the central straight waveguides (4 parallel lines)
    straight_length = 120.0
    straight_gap = 0.5
    central_straights = []
    
    for i in range(4):
        straight = c << gf.components.straight(length=straight_length, cross_section=xs)
        straight.move((0, i * (0.5 + straight_gap)))
        central_straights.append(straight)
    
    # Create top S-bend structure
    # First, create the S-bend component
    s_bend_size = (60.0, 30.0)  # (dx, dy)
    s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    s_bend.move((0, 30.0))  # Position above central straights
    
    # Create top waveguide segments that connect to S-bend
    top_wg_length = 30.0
    top_wgs = []
    
    for i in range(4):
        # Create a straight waveguide
        top_wg = c << gf.components.straight(length=top_wg_length, cross_section=xs)
        top_wg.move((0, 30.0 + s_bend_size[1] + i * (0.5 + straight_gap)))
        top_wgs.append(top_wg)
        
        # Connect to S-bend
        # This is a simplified connection - in practice, you'd need to align ports properly
        # For this recreation, we'll assume the S-bend is positioned to connect
    
    # Create bottom S-bend structure (mirrored)
    bottom_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    bottom_s_bend.move((0, -s_bend_size[1] - 30.0))
    bottom_s_bend.mirror()
    
    # Create bottom waveguide segments
    bottom_wgs = []
    
    for i in range(4):
        bottom_wg = c << gf.components.straight(length=top_wg_length, cross_section=xs)
        bottom_wg.move((0, -s_bend_size[1] - 30.0 - top_wg_length - i * (0.5 + straight_gap)))
        bottom_wgs.append(bottom_wg)
        
        # Connect to bottom S-bend (simplified)

    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")