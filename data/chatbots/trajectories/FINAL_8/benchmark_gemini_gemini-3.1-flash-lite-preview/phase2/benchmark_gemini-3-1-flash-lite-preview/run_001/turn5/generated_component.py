import gdsfactory as gf

@gf.cell
def single_fan_out_waveguide(angle=0.0, length=20.0, radius=20.0):
    """
    Creates a single waveguide element: Bend -> Straight -> Bend.
    Handles angle=0 explicitly to prevent ZeroDivisionError.
    """
    c = gf.Component()
    xs = gf.cross_section.strip()
    
    # 1. Logic for center waveguide (angle=0)
    # If angle is effectively 0, just return a straight waveguide.
    if abs(angle) < 1e-3:
        straight = c << gf.components.straight(length=length + 2*radius, cross_section=xs)
        c.add_port("o1", port=straight.ports["o1"])
        c.add_port("o2", port=straight.ports["o2"])
        return c

    # 2. Logic for fanning waveguides
    # We create the straight section first
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Create the two bends
    # Positive angle bends up, negative angle bends down (or vice versa depending on orientation)
    b_left = c << gf.components.bend_euler(radius=radius, angle=angle, cross_section=xs)
    b_right = c << gf.components.bend_euler(radius=radius, angle=angle, cross_section=xs)
    
    # 3. Connect the components
    # Connect left bend o2 to straight o1
    b_left.connect("o2", wg.ports["o1"])
    # Connect right bend o1 to straight o2
    b_right.connect("o1", wg.ports["o2"])
    
    # 4. Add ports
    c.add_port("o1", port=b_left.ports["o1"])
    c.add_port("o2", port=b_right.ports["o2"])
    
    return c

@gf.cell
def fan_out_device():
    """
    Assembles the fan-out array using the robust single_fan_out_waveguide.
    """
    c = gf.Component()
    
    num_waveguides = 5
    pitch = 5.0  # Vertical spacing
    
    # Generate 5 waveguides
    for i in range(num_waveguides):
        # Calculate offset from center
        y_offset = (i - num_waveguides // 2) * pitch
        
        # Calculate angle:
        # Center (i=2) results in 0. Outer results in +/- 20
        angle = (i - num_waveguides // 2) * 20.0
        
        # Add the component
        wg = c << single_fan_out_waveguide(angle=angle, length=20, radius=20)
        
        # Position them
        wg.movey(y_offset)
        
    return c

# Generate and save
device = fan_out_device()
device.write_gds("fan_out_device_final.gds")