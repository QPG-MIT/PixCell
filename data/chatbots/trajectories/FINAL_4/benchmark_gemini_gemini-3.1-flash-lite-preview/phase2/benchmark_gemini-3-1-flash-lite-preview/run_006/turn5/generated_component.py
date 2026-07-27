import gdsfactory as gf

@gf.cell
def coupler_smooth():
    """
    Creates a directional coupler with symmetric adiabatic Euler bends.
    Total length ~18um to match the target footprint.
    """
    c = gf.Component()
    
    # Define a standard strip waveguide cross-section
    xs = gf.cross_section.strip(width=0.5, layer=(1, 0))
    
    # 1. Define the PATH for the top waveguide
    # Sequence: Start -> Bend Down -> Coupling Region -> Bend Up -> End
    p_top = gf.Path()
    p_top.append(gf.path.straight(length=4))
    p_top.append(gf.path.euler(radius=5, angle=-30)) # Bend Down
    p_top.append(gf.path.straight(length=6))           # Coupling Section
    p_top.append(gf.path.euler(radius=5, angle=30))    # Bend Up
    p_top.append(gf.path.straight(length=4))
    
    # 2. Define the PATH for the bottom waveguide
    # This is the vertical mirror of the top path to create symmetry
    p_bot = gf.Path()
    p_bot.append(gf.path.straight(length=4))
    p_bot.append(gf.path.euler(radius=5, angle=30))    # Bend Up (Mirrored)
    p_bot.append(gf.path.straight(length=6))           # Coupling Section
    p_bot.append(gf.path.euler(radius=5, angle=-30))   # Bend Down (Mirrored)
    p_bot.append(gf.path.straight(length=4))

    # 3. Extrude paths into waveguide geometry
    w1 = c << gf.path.extrude(p_top, cross_section=xs)
    w2 = c << gf.path.extrude(p_bot, cross_section=xs)
    
    # 4. Position waveguides
    # We offset them so the coupling region has a specific small gap
    w1.movey(0.5) 
    w2.movey(-0.5)
    
    return c

if __name__ == "__main__":
    device = coupler_smooth()
    device.write_gds("coupler_smooth.gds")
    device.show()
    print("GDS file generated with symmetric S-bend geometry.")