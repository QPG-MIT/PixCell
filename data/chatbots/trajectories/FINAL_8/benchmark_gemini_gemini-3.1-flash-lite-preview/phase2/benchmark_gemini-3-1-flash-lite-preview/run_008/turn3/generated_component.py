import gdsfactory as gf

@gf.cell
def flared_layout():
    """
    Creates a flared (fan-out) waveguide structure.
    The central waveguide is straight, and the outer waveguides 
    bend outwards to create a symmetric flare.
    """
    c = gf.Component()
    
    # Define a standard cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Offsets for the 5 waveguides: 
    # [20, 10] will bend up, [0] stays straight, [-10, -20] will bend down.
    y_offsets = [20, 10, 0, -10, -20]
    
    for y in y_offsets:
        if y == 0:
            # Middle waveguide is straight
            wg = c << gf.components.straight(length=120, cross_section=xs)
        else:
            # Other waveguides are S-bends to create the flare.
            # bend_s will shift the waveguide vertically by `y`.
            wg = c << gf.components.bend_s(size=(120, y), cross_section=xs)
        
        # Move the start of each waveguide to its specific y-offset 
        # so they are parallel at the start and end.
        wg.movey(y)
        
    return c

if __name__ == "__main__":
    # Generate the device
    device = flared_layout()
    
    # Save the GDS file
    device.write_gds("final_layout.gds")
    print("Device generated successfully as final_layout.gds")