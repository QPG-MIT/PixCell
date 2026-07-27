import gdsfactory as gf

@gf.cell
def dense_waveguide_coupler():
    c = gf.Component()

    # Parameters derived from footprint [120, 4] and visual inspection
    # 12 lines total fit in 4um height -> pitch approx 0.33um
    width = 0.15
    gap = 0.18
    pitch = width + gap
    
    n_center = 4  # Number of straight center waveguides
    n_outer = 4   # Number of top/bottom waveguides
    
    # Dimensions
    total_length = 120.0      # Full length of the center straight section
    coupling_length = 80.0    # Length of the parallel section for top/bottom buses
    r_min = 10.0              # Minimum bend radius for the inner-most curved waveguide
    
    # Define Cross Section
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # 1. Center Bus: Straight waveguides running the full length
    # Centered vertically around y=0
    y_center_start = -((n_center - 1) * pitch) / 2
    
    for i in range(n_center):
        y = y_center_start + i * pitch
        wg = c << gf.components.straight(length=total_length, cross_section=xs)
        wg.center = (0, y)

    # 2. Top Bus: Nested waveguides bending UP (North)
    # The first line starts `pitch` distance above the center bus
    y_top_start = y_center_start + (n_center - 1) * pitch + pitch
    
    for i in range(n_outer):
        # Calculate radius and y-position for nested structure
        # i=0 is the innermost (closest to center)
        radius = r_min + i * pitch
        y = y_top_start + i * pitch
        
        # Horizontal straight section
        wg = c << gf.components.straight(length=coupling_length, cross_section=xs)
        wg.center = (0, y)
        
        # Left Bend: Connects to West port ("o1"), bends UP (North)
        # We attach the 'o1' port of the bend to the 'o1' port of the straight WG.
        # Standard bend goes East->North. 
        # No transformation needed for 'o1' (East) to connect to straight 'o1' (West)? 
        # No, straight 'o1' faces West. Bend 'o1' faces East. They mate.
        # Result: The bend starts at straight's left end and curves North.
        b_l = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
        b_l.connect("o1", wg.ports["o1"])
        
        # Right Bend: Connects to East port ("o2"), bends UP (North)
        # We attach the 'o1' port of the bend to the 'o2' port of the straight WG.
        # Straight 'o2' faces East. We need bend 'o1' to face West.
        # Mirroring the bend around X-axis makes 'o1' face West and 'o2' face North.
        b_r = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
        b_r.mirror_x()
        b_r.connect("o1", wg.ports["o2"])

    # 3. Bottom Bus: Nested waveguides bending DOWN (South)
    # The first line starts `pitch` distance below the center bus
    y_bottom_start = y_center_start - pitch
    
    for i in range(n_outer):
        # i=0 is the innermost (closest to center)
        radius = r_min + i * pitch
        y = y_bottom_start - i * pitch
        
        # Horizontal straight section
        wg = c << gf.components.straight(length=coupling_length, cross_section=xs)
        wg.center = (0, y)
        
        # Left Bend: Connects to West port ("o1"), bends DOWN (South)
        # Standard bend (East->North). Mirror Y -> (East->South).
        # Connects to straight 'o1' (West).
        b_l = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
        b_l.mirror_y()
        b_l.connect("o1", wg.ports["o1"])
        
        # Right Bend: Connects to East port ("o2"), bends DOWN (South)
        # Standard bend. Mirror X -> (West->North). Mirror Y -> (West->South).
        # Connects to straight 'o2' (East).
        b_r = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
        b_r.mirror_x()
        b_r.mirror_y()
        b_r.connect("o1", wg.ports["o2"])

    return c

# Generate the device
device = dense_waveguide_coupler()
device.write_gds("dense_coupler.gds")