import gdsfactory as gf

@gf.cell
def coupler_smooth():
    """
    Creates a directional coupler using smooth path interpolation
    with a larger radius to ensure continuous curvature.
    """
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0)
    )
    
    # 1. Define waypoints for the TOP waveguide
    # These points create a flat start, a smooth dip, and a flat end.
    # Radius=6 ensures the transition is curved rather than angular.
    top_points = [
        (0, 1.5), 
        (5, 1.5), 
        (9, 0.5), 
        (13, 1.5), 
        (18, 1.5)
    ]
    
    # 2. Define waypoints for the BOTTOM waveguide (Mirror of top)
    bot_points = [
        (0, -1.5), 
        (5, -1.5), 
        (9, -0.5), 
        (13, -1.5), 
        (18, -1.5)
    ]
    
    # 3. Create smooth paths with a larger radius to prevent 'kinks'
    # The radius parameter defines how much the path 'fillets' the corners.
    path_top = gf.path.smooth(points=top_points, radius=6.0)
    path_bot = gf.path.smooth(points=bot_points, radius=6.0)
    
    # 4. Extrude paths into waveguide geometry
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bot, cross_section=xs)
    
    return c

if __name__ == "__main__":
    device = coupler_smooth()
    device.write_gds("coupled_waveguides_smooth.gds")
    device.show()
    print("GDS file generated with improved smooth geometry.")