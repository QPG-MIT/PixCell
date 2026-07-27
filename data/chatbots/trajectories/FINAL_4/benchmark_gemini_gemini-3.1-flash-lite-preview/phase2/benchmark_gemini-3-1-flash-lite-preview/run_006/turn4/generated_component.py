import gdsfactory as gf

@gf.cell
def coupler_smooth():
    """
    Creates a directional coupler using adiabatic Euler bends
    for perfectly smooth, continuous sinusoidal transitions.
    """
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0)
    )
    
    # 1. Define TOP path: Straight -> Euler(down) -> Euler(up) -> Straight
    p_top = gf.Path()
    p_top.append(gf.path.straight(length=5))
    p_top.append(gf.path.euler(radius=6, angle=15))
    p_top.append(gf.path.euler(radius=6, angle=-15))
    p_top.append(gf.path.straight(length=5))
    
    # 2. Define BOTTOM path: Straight -> Euler(up) -> Euler(down) -> Straight
    p_bot = gf.Path()
    p_bot.append(gf.path.straight(length=5))
    p_bot.append(gf.path.euler(radius=6, angle=-15))
    p_bot.append(gf.path.euler(radius=6, angle=15))
    p_bot.append(gf.path.straight(length=5))
    
    # 3. Extrude paths into waveguide geometry
    # We create them at (0,0) and move them to their correct initial y-offsets
    w1 = c << gf.path.extrude(p_top, cross_section=xs)
    w2 = c << gf.path.extrude(p_bot, cross_section=xs)
    
    # Position them to create the coupler gap
    w1.movey(1.25)
    w2.movey(-1.25)
    
    return c

if __name__ == "__main__":
    device = coupler_smooth()
    device.write_gds("coupled_waveguides_euler.gds")
    device.show()
    print("GDS file generated with smooth Euler geometry.")