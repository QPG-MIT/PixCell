import gdsfactory as gf

@gf.cell
def recreate_s_bend_device():
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Total dimensions from footprint
    total_length = 120.0  # from footprint
    total_width = 4.0     # from footprint
    
    # Create a single continuous S-bend path
    # We'll use the path system for more precise control
    
    # Create a path with the S-bend shape
    path = gf.Path()
    
    # Start with a straight section
    path.append(gf.path.straight(length=total_length/3))
    
    # Add an Euler bend (upward curve)
    path.append(gf.path.euler(radius=total_width/2, angle=90, p=0.5))
    
    # Add a straight section in the middle
    path.append(gf.path.straight(length=total_length/3))
    
    # Add another Euler bend (downward curve to return to original height)
    path.append(gf.path.euler(radius=total_width/2, angle=-90, p=0.5))
    
    # Add final straight section
    path.append(gf.path.straight(length=total_length/3))
    
    # Extrude the path to create the waveguide
    waveguide = c << gf.path.extrude(path, cross_section=xs)
    
    # Add ports at the beginning and end
    c.add_port("o1", port=waveguide.ports["o1"])
    c.add_port("o2", port=waveguide.ports["o2"])
    
    return c

# Create and save the device
device = recreate_s_bend_device()
device.write_gds("recreated_s_bend_device.gds")