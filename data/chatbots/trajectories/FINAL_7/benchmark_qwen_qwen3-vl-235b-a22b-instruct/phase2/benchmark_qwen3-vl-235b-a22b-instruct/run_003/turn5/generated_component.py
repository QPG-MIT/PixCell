import gdsfactory as gf

@gf.cell
def tapered_waveguide():
    c = gf.Component()
    
    # Define cross-section for the waveguide
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=1.0  # Min bend radius
    )
    
    # Create straight segment
    straight = c << gf.components.straight(length=2.0, cross_section=xs)
    
    # Create 90-degree Euler bend
    bend = c << gf.components.bend_euler(radius=1.0, angle=90, cross_section=xs)
    
    # Connect bend to straight
    bend.connect("o1", straight.ports["o2"])
    
    # Create taper from 0.5 to 0.1 width
    taper = c << gf.components.taper(length=1.0, width1=0.5, width2=0.1)
    
    # Connect taper to bend
    taper.connect("o1", bend.ports["o2"])
    
    # Add ports
    c.add_port("o1", port=straight.ports["o1"])
    c.add_port("o2", port=taper.ports["o2"])
    
    return c

# Create the device
device = tapered_waveguide()
device.write_gds("tapered_waveguide.gds")