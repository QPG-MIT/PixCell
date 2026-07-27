import gdsfactory as gf

@gf.cell
def fan_out_device():
    """
    Creates a symmetric 5-waveguide fan-out structure.
    Handles the center waveguide specifically to avoid ZeroDivisionError.
    """
    c = gf.Component()
    # Define a thin cross-section
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))
    
    # Device parameters
    pitch = 2.0             # Vertical separation between waveguides
    bend_radius = 20.0      # Radius of the Euler bends
    straight_length = 40.0  # Length of the middle straight section
    
    # Iterate through the 5 waveguides (i = -2, -1, 0, 1, 2)
    for i in range(-2, 3):
        # 1. Construct the path
        if i == 0:
            # Center waveguide: Just a straight path
            # We match the total length of the other waveguides (2 bends + straight)
            # for visual symmetry.
            p = gf.Path()
            p.append(gf.path.straight(length=straight_length + 2 * bend_radius))
            wg = gf.path.extrude(p, cross_section=xs)
        else:
            # Off-center waveguides: Use S-bend logic
            # Angle increases for waveguides further from center
            angle = 15 * i 
            
            p = gf.Path()
            # First bend: deviate from the straight path
            p.append(gf.path.euler(radius=bend_radius, angle=angle))
            # Straight section
            p.append(gf.path.straight(length=straight_length))
            # Second bend: return to parallel (the reverse angle)
            p.append(gf.path.euler(radius=bend_radius, angle=-angle))
            
            # 2. Extrude the path
            wg = gf.path.extrude(p, cross_section=xs)
        
        # 3. Add to component
        ref = c << wg
        
        # Move the waveguide to its correct vertical position in the stack
        ref.movey(i * pitch)
        
    return c

# Create and write the GDS
device = fan_out_device()
device.write_gds("fan_out_device.gds")