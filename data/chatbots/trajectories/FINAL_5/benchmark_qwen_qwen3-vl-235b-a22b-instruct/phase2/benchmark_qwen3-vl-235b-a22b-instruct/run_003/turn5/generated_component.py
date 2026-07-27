import gdsfactory as gf

@gf.cell
def create_vertical_waveguide():
    c = gf.Component()
    
    # Create a simple cross-section
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=5.0,
        radius_min=3.0
    )
    
    # Create a straight vertical waveguide
    # The target appears to be a single vertical line, so we'll create a straight waveguide
    waveguide = c << gf.components.straight(length=10, cross_section=xs)
    
    # Rotate the waveguide to make it vertical (90 degrees)
    waveguide.rotate(90)
    
    # Center the component for better visualization
    waveguide.move((0, 0))
    
    return c

# Create and save the device
device = create_vertical_waveguide()
device.write_gds("vertical_waveguide.gds")