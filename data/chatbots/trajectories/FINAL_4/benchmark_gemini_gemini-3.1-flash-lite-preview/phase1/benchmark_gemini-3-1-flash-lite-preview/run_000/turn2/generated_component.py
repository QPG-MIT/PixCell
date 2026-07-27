import gdsfactory as gf

@gf.cell
def parametric_coupler():
    """
    Creates the symmetric curved coupler geometry using the 
    fundamental Path constructor to avoid library dependencies.
    """
    c = gf.Component()
    
    # 1. Define the cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Define the Paths using coordinate points
    # We define the waypoints to create the narrowing and widening coupler shape.
    # Total length is 18um (-9 to 9)
    # The 'y' values create the gentle curve to minimize the gap in the center.
    
    # Top waveguide path points
    points_top = [(-9, 0.75), (-4.5, 0.25), (0, 0.25), (4.5, 0.25), (9, 0.75)]
    path_top = gf.Path(points_top)
    
    # Bottom waveguide path points (mirrored)
    points_bot = [(-9, -0.75), (-4.5, -0.25), (0, -0.25), (4.5, -0.25), (9, -0.75)]
    path_bot = gf.Path(points_bot)

    # 3. Extrude the paths into components
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bot, cross_section=xs)

    return c

if __name__ == "__main__":
    # Generate the component
    device = parametric_coupler()
    
    # Write the GDS file
    device.write_gds("parametric_coupler.gds")
    
    print("GDS file 'parametric_coupler.gds' successfully created.")