import gdsfactory as gf

@gf.cell
def fan_out_device():
    """
    Creates a symmetric 5-waveguide fan-out structure.
    """
    c = gf.Component()
    
    # Define a thin cross-section
    xs = gf.cross_section.cross_section(width=0.4, layer=(1, 0))
    
    # Device parameters
    num_waveguides = 5
    straight_length = 60.0
    bend_radius = 20.0
    pitch = 1.5 # Vertical separation between waveguides
    
    # Angles for each waveguide (symmetrical: top waveguides bend up, bottom bend down)
    # 0 is the center waveguide
    angles = [-20, -10, 0, 10, 20] 

    for i in range(num_waveguides):
        angle = angles[i]
        
        # 1. Construct the path
        # If angle is 0, just a straight line.
        # Otherwise, a symmetric S-shape: Bend -> Straight -> Bend
        if abs(angle) < 1e-6:
            p = gf.Path()
            p.append(gf.path.straight(length=straight_length + 2 * bend_radius))
        else:
            p = gf.Path()
            # Bend (out) -> Straight -> Bend (back to parallel)
            # We use half the total length for the center to keep it centered
            p.append(gf.path.euler(radius=bend_radius, angle=angle))
            p.append(gf.path.straight(length=straight_length))
            p.append(gf.path.euler(radius=bend_radius, angle=-angle))
        
        # 2. Extrude the path
        wg = gf.path.extrude(p, cross_section=xs)
        
        # 3. Add to component
        ref = c << wg
        
        # Move the waveguide into its vertical position
        # We center the stack around y=0
        y_offset = (i - 2) * pitch
        ref.movey(y_offset)
        
    return c

# Create and write the GDS
device = fan_out_device()
device.write_gds("fan_out_device.gds")