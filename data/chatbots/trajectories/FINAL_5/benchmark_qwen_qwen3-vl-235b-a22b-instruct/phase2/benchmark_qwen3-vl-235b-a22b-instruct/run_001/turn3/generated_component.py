import gdsfactory as gf

@gf.cell
def create_grating_coupler_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=10.0,
        radius_min=10.0
    )
    
    # Create the central rectangular region
    central_width = 18.24  # Matches the footprint constraint
    central_height = 0.7   # Matches the footprint constraint
    central_region = c << gf.components.rectangle(
        size=(central_width, central_height), 
        layer=(1, 0),
        centered=True
    )
    
    # Create the grating structures on both sides of the central region
    grating_period = 0.5
    grating_width = 0.2
    grating_length = 1.0  # Length of each grating tooth
    num_gratings = int(central_height / grating_period)
    
    # Create grating teeth on the left side of the central region
    for i in range(num_gratings):
        y_pos = -central_height/2 + i * grating_period + grating_period/2
        
        # Create left grating tooth
        left_grating = c << gf.components.rectangle(
            size=(grating_length, grating_width), 
            layer=(1, 0),
            centered=True
        )
        left_grating.move((-central_width/2 - grating_length/2, y_pos))
    
    # Create grating teeth on the right side of the central region
    for i in range(num_gratings):
        y_pos = -central_height/2 + i * grating_period + grating_period/2
        
        # Create right grating tooth
        right_grating = c << gf.components.rectangle(
            size=(grating_length, grating_width), 
            layer=(1, 0),
            centered=True
        )
        right_grating.move((central_width/2 + grating_length/2, y_pos))
    
    # Manually add ports on the left and right edges of the central region
    # Port on the left edge (facing left)
    c.add_port(
        name="o1",
        center=(-central_width/2, 0),
        width=central_height,
        orientation=180,
        layer=(1, 0)
    )
    
    # Port on the right edge (facing right)
    c.add_port(
        name="o2",
        center=(central_width/2, 0),
        width=central_height,
        orientation=0,
        layer=(1, 0)
    )
    
    return c

# Create and save the device
device = create_grating_coupler_device()
device.write_gds("grating_coupler_device.gds")