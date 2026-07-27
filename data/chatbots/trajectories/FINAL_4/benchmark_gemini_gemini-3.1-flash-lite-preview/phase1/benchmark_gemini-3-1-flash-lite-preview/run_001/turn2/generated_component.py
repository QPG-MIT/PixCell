import gdsfactory as gf

@gf.cell
def symmetric_tapered_coupler():
    c = gf.Component()
    
    # 1. Define standard waveguide cross-section
    # Width 0.5um, layer 1
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # 2. Build the top path (S-bend shape)
    # We use a sequence of straight segments and arcs to create the waist
    # To get a smooth transition, we use small angles.
    p_top = gf.Path()
    p_top.append(gf.path.straight(length=5))
    p_top.append(gf.path.arc(radius=20, angle=-10)) # Curve in
    p_top.append(gf.path.arc(radius=20, angle=10))  # Curve out to parallel
    p_top.append(gf.path.straight(length=5))
    
    # 3. Build the bottom path (Mirror of top)
    p_bot = gf.Path()
    p_bot.append(gf.path.straight(length=5))
    p_bot.append(gf.path.arc(radius=20, angle=10))  # Curve in (opposite)
    p_bot.append(gf.path.arc(radius=20, angle=-10)) # Curve out (opposite)
    p_bot.append(gf.path.straight(length=5))
    
    # 4. Extrude the paths
    # We move them to their starting Y-positions to create the gap
    # A shift of +/- 0.3um creates a tight coupling waist
    top_wg = gf.path.extrude(p_top, cross_section=xs)
    bot_wg = gf.path.extrude(p_bot, cross_section=xs)
    
    # Add to component with Y-offset to define the gap
    c << top_wg.movey(0.3)
    c << bot_wg.movey(-0.3)
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = symmetric_tapered_coupler()
    
    # Explicitly write the GDS file
    device.write_gds("tapered_coupler.gds")
    print("GDS file 'tapered_coupler.gds' produced.")