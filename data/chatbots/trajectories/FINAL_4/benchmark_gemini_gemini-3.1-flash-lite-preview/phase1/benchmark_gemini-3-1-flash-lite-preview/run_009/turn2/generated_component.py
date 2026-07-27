import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    """
    Creates an adiabatic coupler using the gf.path.smooth function.
    This creates a smooth, continuous path that fits the 18um x 3um footprint.
    """
    c = gf.Component("adiabatic_coupler")
    
    # Define a standard waveguide cross-section (width=0.5um)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Define the coordinates for the center-line of the waveguides
    # We want to start at y=1.25 and y=-1.25, 
    # move to the center (y=0.25 and y=-0.25) at the 9um mark,
    # then move back to the start position at 18um.
    top_points = [(0, 1.25), (9, 0.25), (18, 1.25)]
    bottom_points = [(0, -1.25), (9, -0.25), (18, -1.25)]
    
    # Create the paths using the smooth function listed in your catalog.
    # The radius parameter controls how "soft" the transition is.
    path_top = gf.path.smooth(points=top_points, radius=5)
    path_bottom = gf.path.smooth(points=bottom_points, radius=5)
    
    # Extrude the paths into physical waveguide geometry
    top_wg = gf.path.extrude(path_top, cross_section=xs)
    bottom_wg = gf.path.extrude(path_bottom, cross_section=xs)
    
    # Add the resulting components to our main cell
    c << top_wg
    c << bottom_wg
    
    # Explicitly write the GDS file
    c.write_gds("adiabatic_coupler.gds")
    
    return c

if __name__ == "__main__":
    # Generate the component and write the GDS file
    device = adiabatic_coupler()
    print("GDS file 'adiabatic_coupler.gds' successfully produced.")