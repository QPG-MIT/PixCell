import gdsfactory as gf

@gf.cell
def coupled_waveguides():
    c = gf.Component()
    
    # 1. Define the cross-section as per the catalog
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Define the path points
    # We use waypoints to define the start, the coupling waist, and the end.
    # The X-coordinates span -9 to 9 (Total 18um)
    # The Y-coordinates span -1.25 to 1.25 (Total 2.5um, fitting the 3um footprint)
    points_top = [(-9, 1.25), (0, 0.35), (9, 1.25)]
    points_bot = [(-9, -1.25), (0, -0.35), (9, -1.25)]

    # 3. Create paths using gf.path.smooth
    # The radius parameter controls the sharpness of the curve transition
    p_top = gf.path.smooth(points=points_top, radius=5.0)
    p_bot = gf.path.smooth(points=points_bot, radius=5.0)

    # 4. Extrude paths into components
    wg_top = c << gf.path.extrude(p_top, cross_section=xs)
    wg_bot = c << gf.path.extrude(p_bot, cross_section=xs)

    return c

# Generate and save
device = coupled_waveguides()
device.write_gds("coupled_waveguides.gds")