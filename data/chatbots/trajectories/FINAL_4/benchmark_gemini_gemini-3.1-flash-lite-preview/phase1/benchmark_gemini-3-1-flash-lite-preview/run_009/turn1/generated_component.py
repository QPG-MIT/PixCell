import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    """
    Creates an adiabatic coupler structure using GDSFactory parametric primitives.
    Fits within the 18um x 3um footprint.
    """
    c = gf.Component("adiabatic_coupler")
    
    # Define a standard waveguide cross-section (width=0.5um, layer 1)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Parameters for the 18um x 3um footprint
    # We position the waveguides at y=+1.25 and y=-1.25 (total 2.5um span).
    # Adding the 0.5um waveguide width results in a total 3.0um height.
    length = 18.0
    y_start = 1.25
    y_end = 0.25
    dy = y_end - y_start  # Movement required: -1.0um for top, +1.0um for bottom
    
    # Create the two S-bend waveguides using the 'bend_s' primitive
    # The 'size' parameter is (dx, dy)
    top_wg = c << gf.components.bend_s(size=(length, dy), cross_section=xs)
    bottom_wg = c << gf.components.bend_s(size=(length, -dy), cross_section=xs)
    
    # Position the waveguides
    top_wg.movey(y_start)
    bottom_wg.movey(-y_start)
    
    # Add ports to satisfy component interface requirements
    c.add_port("o1", port=top_wg.ports["o1"])
    c.add_port("o2", port=top_wg.ports["o2"])
    c.add_port("o3", port=bottom_wg.ports["o1"])
    c.add_port("o4", port=bottom_wg.ports["o2"])
    
    # Explicitly write the GDS file
    c.write_gds("adiabatic_coupler.gds")
    
    return c

if __name__ == "__main__":
    # Generate the component and write the GDS file
    device = adiabatic_coupler()
    print("GDS file 'adiabatic_coupler.gds' successfully produced.")