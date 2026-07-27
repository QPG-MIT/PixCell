import gdsfactory as gf

@gf.cell
def coupler_smooth():
    """
    Creates a directional coupler using smooth path interpolation.
    """
    c = gf.Component()
    
    # Define cross-section with a smaller radius to allow for tight coupling
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0), 
        radius=2.0
    )
    
    # 1. Define waypoints for the TOP waveguide
    # Start at Y=1.5, move to Y=0.5 (coupling height), end at Y=1.5
    top_points = [
        (0, 1.5), 
        (6, 1.5), 
        (9, 0.5), 
        (12, 0.5), 
        (18, 1.5)
    ]
    
    # 2. Define waypoints for the BOTTOM waveguide (Mirror of top)
    bot_points = [
        (0, -1.5), 
        (6, -1.5), 
        (9, -0.5), 
        (12, -0.5), 
        (18, -1.5)
    ]
    
    # 3. Create paths
    # We use radius=2.0 to ensure a smooth transition within the small footprint
    path_top = gf.path.smooth(points=top_points, radius=2.0)
    path_bot = gf.path.smooth(points=bot_points, radius=2.0)
    
    # 4. Extrude paths into waveguide geometry
    wg_top = c << gf.path.extrude(path_top, cross_section=xs)
    wg_bot = c << gf.path.extrude(path_bot, cross_section=xs)
    
    return c

if __name__ == "__main__":
    device = coupler_smooth()
    device.write_gds("coupled_waveguides_smooth.gds")
    device.show()
    print("GDS file generated successfully with smooth geometry.")