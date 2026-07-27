import gdsfactory as gf

@gf.cell
def parametric_coupler():
    """
    Creates the symmetric curved coupler geometry using 
    the native bend_s primitive from the catalog.
    """
    c = gf.Component()
    
    # 1. Define the cross-section
    # Using a 0.5um width to fit the 3um vertical footprint
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Define the S-bend components
    # bend_s creates an S-curve. 
    # Size (dx, dy) = (18, dy).
    # We create two S-bends and move them to separate them vertically.
    
    # Top waveguide: curves downwards (negative dy)
    s_bend_top = c << gf.components.bend_s(size=(18, -0.8), cross_section=xs)
    
    # Bottom waveguide: curves upwards (positive dy)
    s_bend_bot = c << gf.components.bend_s(size=(18, 0.8), cross_section=xs)

    # 3. Position the components
    # We move them apart vertically to create the coupler appearance
    s_bend_top.movey(0.6)
    s_bend_bot.movey(-0.6)

    return c

if __name__ == "__main__":
    # Generate the component
    device = parametric_coupler()
    
    # Write the GDS file
    device.write_gds("parametric_coupler.gds")
    
    # Verification
    print("GDS file 'parametric_coupler.gds' successfully created.")