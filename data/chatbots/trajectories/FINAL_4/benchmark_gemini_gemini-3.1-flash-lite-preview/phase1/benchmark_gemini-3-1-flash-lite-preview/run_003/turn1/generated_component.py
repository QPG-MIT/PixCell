import gdsfactory as gf

@gf.cell
def custom_coupler():
    """
    Creates a smooth coupler device using two symmetric bend_s primitives.
    """
    c = gf.Component()
    
    # Define a standard waveguide cross-section
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))
    
    # bend_s creates an adiabatic S-bend from (0,0) to (dx, dy).
    # We use a size of (18, -0.3) to span the 18um length 
    # and create a shallow S-curve with a 0.3um vertical dip.
    # A total vertical displacement of 0.3um makes the waveguides 
    # move 0.6um closer together in the middle.
    
    # Top waveguide: Starts at y=0.5, ends at y=0.2 (18, -0.3 relative)
    top_waveguide = c << gf.components.bend_s(size=(18, -0.3), cross_section=xs)
    top_waveguide.movey(0.5)
    
    # Bottom waveguide: Starts at y=-0.5, ends at y=-0.2 (18, 0.3 relative)
    bottom_waveguide = c << gf.components.bend_s(size=(18, 0.3), cross_section=xs)
    bottom_waveguide.movey(-0.5)
    
    return c

# Generate the component
device = custom_coupler()

# Save/Show
device.write_gds("coupler_device.gds")
device.show()