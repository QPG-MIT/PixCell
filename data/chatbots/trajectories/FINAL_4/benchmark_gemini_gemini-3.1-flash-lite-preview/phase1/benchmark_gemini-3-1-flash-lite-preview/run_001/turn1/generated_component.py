import gdsfactory as gf

@gf.cell
def symmetric_tapered_coupler():
    """
    Creates a symmetric pair of curved waveguides using explicit 
    straight and arc paths to ensure compatibility and reliability.
    """
    c = gf.Component()
    
    # 1. Define standard waveguide cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # 2. Build the top path
    # We construct the path using a straight segment, followed by 
    # two arcs to create the gentle "waist" shape.
    p_top = gf.Path()
    p_top.append(gf.path.straight(length=5))
    p_top.append(gf.path.arc(radius=50, angle=10))
    p_top.append(gf.path.arc(radius=50, angle=-10))
    p_top.append(gf.path.straight(length=5))
    
    # 3. Build the bottom path (mirroring the top)
    # We create the path and move it to -0.8um Y-offset
    p_bot = gf.Path()
    p_bot.append(gf.path.straight(length=5))
    p_bot.append(gf.path.arc(radius=50, angle=-10))
    p_bot.append(gf.path.arc(radius=50, angle=10))
    p_bot.append(gf.path.straight(length=5))
    
    # 4. Extrude the paths into 2D geometry
    # We move the bottom path to be symmetric across the x-axis
    wg_top = c << gf.path.extrude(p_top, cross_section=xs)
    wg_top.movey(0.4)
    
    wg_bot = c << gf.path.extrude(p_bot, cross_section=xs)
    wg_bot.movey(-0.4)
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = symmetric_tapered_coupler()
    
    # Explicitly write the GDS file
    device.write_gds("tapered_coupler.gds")
    print("GDS file 'tapered_coupler.gds' successfully produced.")