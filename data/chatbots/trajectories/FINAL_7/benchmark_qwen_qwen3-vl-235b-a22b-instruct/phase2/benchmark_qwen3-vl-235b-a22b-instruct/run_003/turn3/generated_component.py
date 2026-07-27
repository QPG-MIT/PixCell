import gdsfactory as gf

@gf.cell
def single_arc_bend():
    c = gf.Component()
    
    # Define cross-section for the waveguide
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=1.0
    )
    
    # Create a single 180-degree Euler bend
    # This will create a smooth arc similar to the target image
    bend = c << gf.components.bend_euler(radius=1.0, angle=180, cross_section=xs)
    
    # Add ports for connectivity
    c.add_port("o1", port=bend.ports["o1"])
    c.add_port("o2", port=bend.ports["o2"])
    
    return c

# Create the device
device = single_arc_bend()
device.write_gds("single_arc_bend.gds")