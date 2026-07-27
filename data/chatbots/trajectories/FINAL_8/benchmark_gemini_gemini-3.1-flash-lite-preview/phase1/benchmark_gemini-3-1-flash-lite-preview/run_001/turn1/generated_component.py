import gdsfactory as gf

@gf.cell
def fan_out_device():
    """
    Creates a symmetric 5-waveguide fan-out structure 
    using parametric path primitives, with a fix for the 
    ZeroDivisionError on straight segments.
    """
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.2, layer=(1, 0))
    
    # Configuration
    num_waveguides = 5
    straight_length = 60.0
    bend_radius = 20.0
    # Fan angles for 5 waveguides
    angles = [-15, -7.5, 0, 7.5, 15] 

    for i in range(num_waveguides):
        angle = angles[i]
        
        # FIX: Check if angle is 0 to avoid ZeroDivisionError in Euler bend
        if abs(angle) < 1e-6:
            p = gf.path.straight(length=straight_length)
        else:
            # Construct a path: Bend (out) -> Straight -> Bend (in)
            # This maintains parallel output/input alignment
            p = gf.Path()
            p.append(gf.path.euler(radius=bend_radius, angle=angle))
            p.append(gf.path.straight(length=straight_length))
            p.append(gf.path.euler(radius=bend_radius, angle=-angle))
        
        # Extrude the path into a component
        wg = gf.path.extrude(p, cross_section=xs)
        
        # Place the waveguide in the component
        ref = c << wg
        
        # Offset vertically to create the 5-channel fan-out
        ref.movey(i * 0.5)  # 0.5um pitch
        
    return c

# Create and write the GDS
device = fan_out_device()
device.write_gds("fan_out_device.gds")