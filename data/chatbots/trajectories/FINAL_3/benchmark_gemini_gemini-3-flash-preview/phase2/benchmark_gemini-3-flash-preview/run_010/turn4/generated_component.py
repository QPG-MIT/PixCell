import gdsfactory as gf

@gf.cell
def directional_coupler_final():
    """
    Directional coupler matching the target image's visual style and 
    exact 120x4 um footprint.
    Uses Path-based construction for precise control over smooth transitions.
    """
    c = gf.Component("directional_coupler_final")
    
    # 1. Dimensions for [120, 4] footprint
    L = 120.0
    H = 4.0
    width = 0.7   # Thicker waveguides to match visual weight of the target
    gap = 0.3     # Narrow interaction gap
    
    # Calculate vertical centerlines
    # Outer leads: centers at +/- (H/2 - width/2) = +/- 1.65
    # Interaction region: centers at +/- (gap/2 + width/2) = +/- 0.5
    y_outer = (H - width) / 2
    y_inner = (gap + width) / 2
    
    # Horizontal segment allocation: 
    # 20um leads + 15um transitions + 50um middle + 15um transitions + 20um leads = 120um
    l_lead = 20.0
    l_trans = 15.0
    l_mid = L - 2 * (l_lead + l_trans)
    
    # Define horizontal waypoints
    x0 = -L/2
    x1 = x0 + l_lead
    x2 = x1 + l_trans
    x3 = x2 + l_mid
    x4 = x3 + l_trans
    x5 = L/2
    
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # 2. Define Waveguide Paths
    # Waypoints for the top waveguide (stays in positive Y)
    points_top = [
        (x0, y_outer),
        (x1, y_outer),
        (x2, y_inner),
        (x3, y_inner),
        (x4, y_outer),
        (x5, y_outer),
    ]
    
    # Waypoints for the bottom waveguide (stays in negative Y)
    points_bot = [
        (x0, -y_outer),
        (x1, -y_outer),
        (x2, -y_inner),
        (x3, -y_inner),
        (x4, -y_outer),
        (x5, -y_outer),
    ]
    
    # Create smooth paths using Euler transitions. 
    # radius=8.0 provides the tight, distinct "knees" seen in the target image.
    path_top = gf.path.smooth(points=points_top, radius=8.0)
    path_bot = gf.path.smooth(points=points_bot, radius=8.0)
    
    # 3. Extrude Paths into Geometry
    top_wg = c << gf.path.extrude(path_top, cross_section=xs)
    bot_wg = c << gf.path.extrude(path_bot, cross_section=xs)
    
    # 4. Add External Ports
    c.add_port("o1", port=top_wg.ports["o1"])
    c.add_port("o2", port=bot_wg.ports["o1"])
    c.add_port("o3", port=bot_wg.ports["o2"])
    c.add_port("o4", port=top_wg.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the device
    device = directional_coupler_final()
    
    # Print verification of footprint
    print(f"Generated Footprint: {device.xsize:.1f} um x {device.ysize:.1f} um")
    
    # Save and display
    device.write_gds("directional_coupler_final.gds")
    device.show()