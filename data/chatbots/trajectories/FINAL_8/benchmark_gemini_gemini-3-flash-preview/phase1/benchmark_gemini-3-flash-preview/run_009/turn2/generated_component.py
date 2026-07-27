import gdsfactory as gf

@gf.cell
def improved_photonic_taper():
    """
    Recreates the device using gf.path.smooth with a large radius for perfect 
    curvature transitions.
    Footprint: 120um x 4um
    """
    c = gf.Component("smooth_pinched_taper")
    
    # Geometric parameters for visual match
    length = 120.0
    w_line = 0.05      # Thinner lines for higher density
    g_line = 0.04      # Tighter gaps
    w_slab = 0.7       # Substantial slab waveguide
    g_slab_rail = 0.06 # Gap between slab and its line group
    layer = (1, 0)
    
    # 1. Central Horizontal Group (5 lines)
    # These remain straight and centered at Y=0
    xs_line = gf.cross_section.cross_section(width=w_line, layer=layer)
    for i in range(5):
        y_offset = (i - 2) * (w_line + g_line)
        line = c << gf.components.straight(length=length, cross_section=xs_line)
        line.x = 0
        line.y = y_offset

    # 2. Symmetric Horn Arm Component
    @gf.cell
    def make_horn_arm():
        hc = gf.Component()
        
        # Path definitions for the 'pinch' logic
        # y_mid: center of the slab at the device center (pinch point)
        # y_end: center of the slab at the flare ends
        y_mid = 0.82
        y_end = 1.75
        
        # Waypoints for a symmetric "valley" shape
        # We use four points: ends and middle transition points
        pts = [
            (-length/2, y_end), 
            (-20, y_mid), 
            (20, y_mid), 
            (length/2, y_end)
        ]
        
        # Create a path and smooth it with a large radius (45um)
        # This large radius ensures the curve is adiabatic and perfectly smooth.
        p = gf.path.smooth(gf.Path(pts), radius=45)
        
        # Add the slab waveguide
        xs_slab = gf.cross_section.cross_section(width=w_slab, layer=layer)
        hc << gf.path.extrude(p, cross_section=xs_slab)
        
        # Add the 5 thin waveguides on top of the slab
        for i in range(5):
            # Calculate vertical offset from the slab's center path
            offset_from_path = (w_slab / 2) + g_slab_rail + (w_line / 2) + i * (w_line + g_line)
            line_ref = hc << gf.path.extrude(p, cross_section=xs_line)
            line_ref.movey(offset_from_path)
            
        return hc

    # Add the top horn (The "Valley" shape)
    top_horn = c << make_horn_arm()
    
    # Add the bottom horn by mirroring (The "Mountain" shape)
    # Mirroring the valley across the X-axis creates the symmetric pinch
    bottom_horn = c << make_horn_arm()
    bottom_horn.mirror(p1=(0, 0), p2=(1, 0))
    
    # Center the component in the 120x4 footprint
    c.x = 0
    c.y = 0
    
    return c

if __name__ == "__main__":
    # Create and save the component
    component = improved_photonic_taper()
    component.write_gds("improved_photonic_device.gds")