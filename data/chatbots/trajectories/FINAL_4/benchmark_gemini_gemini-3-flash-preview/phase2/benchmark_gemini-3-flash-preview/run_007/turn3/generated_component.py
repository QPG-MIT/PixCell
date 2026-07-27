import gdsfactory as gf

@gf.cell
def create_curved_coupler():
    """
    Recreates the curved directional coupler from the image.
    Dimensions: 18um (Width) x 3um (Height)
    Matches the smooth, symmetric curvature and thick waveguide proportions of the target.
    """
    # 1. Define physical constraints to hit the 18x3um footprint exactly
    target_width = 18.0
    target_height = 3.0
    wg_width = 0.8         # Increased width to match visual weight in original image
    coupling_gap = 0.1     # Narrow gap for the 'waist'
    coupling_length = 0.2  # Very short parallel section for a smooth "pinch" appearance
    
    # 2. Calculate S-bend dimensions
    # Horizontal length of each arm (dx)
    dx = (target_width - coupling_length) / 2.0
    
    # Vertical shift (dy) for the centers of the waveguides
    # Center y-coord at the coupler waist: (gap/2 + width/2)
    y_waist_center = (coupling_gap / 2.0) + (wg_width / 2.0)
    # Center y-coord at the end (to touch the 3um boundary): (target_height/2 - width/2)
    y_end_center = (target_height / 2.0) - (wg_width / 2.0)
    dy = y_end_center - y_waist_center
    
    # 3. Define Cross Section
    xs = gf.cross_section.strip(width=wg_width, layer=(1, 0))
    
    # 4. Create Component
    c = gf.Component("directional_coupler_v2")
    
    # 5. Add the central parallel region
    # We use two straights manually placed to avoid any port-index confusion
    top_center = c << gf.components.straight(length=coupling_length, cross_section=xs)
    bot_center = c << gf.components.straight(length=coupling_length, cross_section=xs)
    
    # Position them symmetrically around the origin
    top_center.movey(y_waist_center)
    top_center.movex(-coupling_length / 2)
    bot_center.movey(-y_waist_center)
    bot_center.movex(-coupling_length / 2)
    
    # 6. Add and connect the S-bend arms
    # For bend_s, port 'o1' is at (0,0) and 'o2' is at (dx, dy).
    
    # Left Side: Connecting bend 'o2' to center 'o1' (left ports)
    # l_top needs to go UP from center to edge, so from center (o2) it moves up to o1. 
    # This means size=(dx, -dy) so that o1 is higher than o2.
    l_top = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    l_bot = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    l_top.connect("o2", top_center.ports["o1"])
    l_bot.connect("o2", bot_center.ports["o1"])
    
    # Right Side: Connecting bend 'o1' to center 'o2' (right ports)
    # r_top moves UP from center to edge.
    r_top = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    r_bot = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    r_top.connect("o1", top_center.ports["o2"])
    r_bot.connect("o1", bot_center.ports["o2"])
    
    # 7. Add external ports
    c.add_port("o1", port=l_top.ports["o1"])
    c.add_port("o2", port=l_bot.ports["o1"])
    c.add_port("o3", port=r_top.ports["o2"])
    c.add_port("o4", port=r_bot.ports["o2"])
    
    return c

if __name__ == "__main__":
    component = create_curved_coupler()
    gds_filename = "curved_coupler_v2.gds"
    component.write_gds(gds_filename)
    
    # Verification of footprint
    try:
        bbox = component.dbbox()
        print(f"Footprint: {bbox.width():.2f}um x {bbox.height():.2f}um")
    except AttributeError:
        print(f"Footprint: {component.xsize:.2f}um x {component.ysize:.2f}um")