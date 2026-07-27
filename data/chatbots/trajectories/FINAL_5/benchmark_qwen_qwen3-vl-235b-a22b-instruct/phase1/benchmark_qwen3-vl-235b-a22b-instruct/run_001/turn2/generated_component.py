import gdsfactory as gf

@gf.cell
def create_s_bend_grating_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=10.0,
        radius_min=10.0
    )
    
    # Create the central straight waveguide
    straight_length = 15.0
    central_waveguide = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # Create the grating structures as perpendicular extensions from the waveguide
    grating_period = 0.5
    grating_width = 0.2
    grating_length = 1.0  # Length of each grating tooth
    num_gratings = int(straight_length / grating_period)
    
    # Create grating teeth on both sides of the central waveguide
    for i in range(num_gratings):
        x_pos = -straight_length/2 + i * grating_period + grating_period/2
        
        # Create top grating tooth
        top_grating = c << gf.components.rectangle(
            size=(grating_width, grating_length), 
            layer=(1, 0),
            centered=True
        )
        top_grating.move((x_pos, grating_length/2))
        
        # Create bottom grating tooth
        bottom_grating = c << gf.components.rectangle(
            size=(grating_width, grating_length), 
            layer=(1, 0),
            centered=True
        )
        bottom_grating.move((x_pos, -grating_length/2))
    
    # Create the top S-bend arm
    top_straight = c << gf.components.straight(length=5.0, cross_section=xs)
    top_straight.move((straight_length/2 + 2.5, 0.7))
    
    top_bend = c << gf.components.bend_euler(radius=10.0, angle=90, cross_section=xs)
    top_bend.connect("o1", top_straight.ports["o2"])
    
    top_curve = c << gf.components.bend_euler(radius=10.0, angle=180, cross_section=xs)
    top_curve.connect("o1", top_bend.ports["o2"])
    
    top_taper = c << gf.components.taper(length=2.0, width1=0.5, width2=0.1)
    top_taper.connect("o1", top_curve.ports["o2"])
    
    # Create the bottom S-bend arm
    bottom_straight = c << gf.components.straight(length=5.0, cross_section=xs)
    bottom_straight.move((straight_length/2 + 2.5, -0.7))
    
    bottom_bend = c << gf.components.bend_euler(radius=10.0, angle=-90, cross_section=xs)
    bottom_bend.connect("o1", bottom_straight.ports["o2"])
    
    bottom_curve = c << gf.components.bend_euler(radius=10.0, angle=-180, cross_section=xs)
    bottom_curve.connect("o1", bottom_bend.ports["o2"])
    
    bottom_taper = c << gf.components.taper(length=2.0, width1=0.5, width2=0.1)
    bottom_taper.connect("o1", bottom_curve.ports["o2"])
    
    # Add ports for external connections
    c.add_port("o1", port=top_taper.ports["o1"])
    c.add_port("o2", port=bottom_taper.ports["o1"])
    
    return c

# Create and save the device
device = create_s_bend_grating_device()
device.write_gds("s_bend_grating_device.gds")