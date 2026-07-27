import gdsfactory as gf

@gf.cell
def tapered_waveguide():
    c = gf.Component()
    
    # Define cross section for the waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a tapered section
    # Start with a narrow width and end with a wider width
    taper_length = 5.0  # Length of the taper
    start_width = 0.3   # Starting width
    end_width = 0.5     # Ending width (same as cross section width)
    
    # Create the taper component
    taper = gf.components.taper(
        length=taper_length,
        width1=start_width,
        width2=end_width
    )
    
    # Create a straight waveguide section to connect to the taper
    straight_length = 3.0
    straight = gf.components.straight(length=straight_length, cross_section=xs)
    
    # Add both components to the main component
    taper_ref = c << taper
    straight_ref = c << straight
    
    # Connect the straight waveguide to the end of the taper
    straight_ref.connect("o1", taper_ref.ports["o2"])
    
    # Add ports for the device
    c.add_port("in", port=taper_ref.ports["o1"])
    c.add_port("out", port=straight_ref.ports["o2"])
    
    return c

# Create the device
device = tapered_waveguide()
device.write_gds("tapered_waveguide.gds")