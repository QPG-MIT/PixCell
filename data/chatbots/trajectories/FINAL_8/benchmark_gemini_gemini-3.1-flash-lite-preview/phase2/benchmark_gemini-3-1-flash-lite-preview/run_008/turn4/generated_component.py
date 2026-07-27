import gdsfactory as gf

@gf.cell
def flared_layout():
    """
    Creates a flared (fan-out) waveguide structure with distinct, separated paths.
    """
    c = gf.Component()
    
    # 1. Reduce cross-section width to ensure lines are distinct in the render
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))
    
    # 2. Define larger vertical offsets and a longer length for a smoother fan-out
    # We create 5 waveguides, each with a different vertical target height
    y_offsets = [40, 20, 0, -20, -40]
    length = 200
    
    for y in y_offsets:
        if y == 0:
            # Middle waveguide is straight
            wg = c << gf.components.straight(length=length, cross_section=xs)
        else:
            # Outer waveguides are S-bends with a vertical displacement of 'y'
            # Using a larger length makes the curve gentler
            wg = c << gf.components.bend_s(size=(length, y), cross_section=xs)
        
    return c

if __name__ == "__main__":
    # Generate the device
    device = flared_layout()
    
    # Save the GDS file
    device.write_gds("final_layout.gds")
    print("Device generated successfully as final_layout.gds")