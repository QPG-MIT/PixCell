import gdsfactory as gf

# Define the cross-section
xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

@gf.cell
def single_unit():
    """
    Creates one 'U' shaped waveguide (Horizontal straight with bends at both ends).
    """
    c = gf.Component()
    
    # 1. Left bend (Curve 90 degrees upwards)
    # bend_euler angle=90 turns 90 degrees counter-clockwise
    b1 = c << gf.components.bend_euler(angle=90, cross_section=xs)
    
    # 2. Middle straight section
    s = c << gf.components.straight(length=20, cross_section=xs)
    
    # 3. Right bend (Curve 90 degrees downwards)
    # Using angle=-90 turns 90 degrees clockwise (completing the U shape)
    b2 = c << gf.components.bend_euler(angle=-90, cross_section=xs)
    
    # Connect the components
    # Connect the output of the left bend to the start of the straight
    b1.connect("o2", s.ports["o1"])
    
    # Connect the end of the straight to the input of the right bend
    b2.connect("o1", s.ports["o2"])
    
    # Return the component with external ports
    c.add_port("o1", port=b1.ports["o1"])
    c.add_port("o2", port=b2.ports["o2"])
    
    return c

@gf.cell
def device_array():
    """
    Creates 5 parallel units stacked vertically.
    """
    c = gf.Component()
    
    num_waveguides = 5
    spacing = 3.0
    
    for i in range(num_waveguides):
        # Create a unit
        unit = c << single_unit()
        
        # Position the unit based on index to create the parallel stack
        # This moves each unit up along the Y-axis
        unit.movey(i * spacing)
        
    return c

# --- Execution ---
if __name__ == "__main__":
    device = device_array()
    
    # Save the file
    device.write_gds("device_fixed.gds")
    
    print("Success: 'device_fixed.gds' produced.")
    # device.show() # Uncomment to open in KLayout