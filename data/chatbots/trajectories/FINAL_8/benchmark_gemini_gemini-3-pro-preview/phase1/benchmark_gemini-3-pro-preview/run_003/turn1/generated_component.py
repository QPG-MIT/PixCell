import gdsfactory as gf

@gf.cell
def device_recreation():
    c = gf.Component()
    
    # Device Constraints
    L_total = 120.0
    H_total = 4.0
    
    # Parameters for dense packing to fit footprint
    n_center = 5       # Number of waveguides in center bundle
    n_side = 4         # Number of waveguides in top/bottom bundles
    width = 0.15       # Waveguide width (um)
    gap = 0.1          # Gap between waveguides (um)
    pitch = width + gap
    gap_major = 0.2    # Gap between center bundle and outer bundles
    
    # Calculate vertical positions
    # Center bundle is centered at y=0
    # Top of center bundle (edge) approx: 2*pitch + width/2
    y_center_max = ((n_center - 1) / 2) * pitch
    
    # Start position for Top Bundle (center of first waveguide)
    y_start_top = y_center_max + width/2 + gap_major + width/2
    
    # Max Y extent (top edge of device)
    Yc = H_total / 2.0
    
    # Determine Curve Geometry
    # To fit within Y=2.0, the bends must connect the horizontal lines to vertical tangents at Y=2.0.
    # For concentric bends opening UP, the center of curvature is at (x, Yc).
    # Radius R = Yc - y_horizontal.
    # Innermost line (lowest y) has Largest Radius.
    # Outermost line (highest y) has Smallest Radius.
    
    # Calculate Max Radius (for the line closest to center)
    R_max = Yc - y_start_top
    
    # Calculate Straight Section Length to fill 120um width
    # Total Width = L_straight + 2 * R_max
    # L_straight = L_total - 2 * R_max
    # We define x_bend as half-length of the straight section
    x_bend = (L_total - 2 * R_max) / 2.0
    
    xs = gf.cross_section.strip(width=width)
    
    # 1. Center Bundle (Straight)
    for i in range(n_center):
        y_pos = (i - (n_center - 1) / 2) * pitch
        # Create straight waveguide
        wg = c << gf.components.straight(length=2*x_bend, cross_section=xs)
        wg.x = 0
        wg.y = y_pos

    # 2. Top Bundle (U-shape opening UP)
    for i in range(n_side):
        # i=0 is bottom (closest to center), i=3 is top (closest to edge)
        y_pos = y_start_top + i * pitch
        R = Yc - y_pos
        
        # Build Path: Start Top-Left -> Curve -> Straight -> Curve -> End Top-Right
        # Start at vertical tangent at left edge (-x_bend - R, Yc)
        # Initialize path direction to South (-90 degrees)
        p = gf.Path([(-x_bend - R, Yc + 0.001), (-x_bend - R, Yc)])
        
        # Arc: Turn Left (South -> East)
        p.append(gf.path.arc(radius=R, angle=90))
        
        # Straight: Horizontal section
        p.append(gf.path.straight(length=2*x_bend))
        
        # Arc: Turn Left (East -> North)
        p.append(gf.path.arc(radius=R, angle=90))
        
        # Extrude and add
        c << p.extrude(xs)
        
    # 3. Bottom Bundle (Inverted U-shape opening DOWN)
    y_start_bot = -y_start_top
    
    for i in range(n_side):
        # i=0 is top (closest to center), i=3 is bottom
        y_pos = y_start_bot - i * pitch
        # Radius is distance from horizontal line to bottom edge (-Yc)
        R = abs(-Yc - y_pos)
        
        # Build Path: Start Bottom-Left -> Curve -> Straight -> Curve -> End Bottom-Right
        # Start at vertical tangent at left edge (-x_bend - R, -Yc)
        # Initialize path direction to North (+90 degrees)
        p = gf.Path([(-x_bend - R, -Yc - 0.001), (-x_bend - R, -Yc)])
        
        # Arc: Turn Right (North -> East)
        p.append(gf.path.arc(radius=R, angle=-90))
        
        # Straight: Horizontal section
        p.append(gf.path.straight(length=2*x_bend))
        
        # Arc: Turn Right (East -> South)
        p.append(gf.path.arc(radius=R, angle=-90))
        
        # Extrude and add
        c << p.extrude(xs)

    return c

# Save the GDS
device = device_recreation()
device.write_gds("device_recreation.gds")