import gdsfactory as gf

@gf.cell
def parametric_device():
    """
    Recreates the device based on the image and footprint constraints.
    Footprint: 120um x 4um.
    Structure: Central straight bus with concentric bent waveguides on top/bottom.
    """
    c = gf.Component()

    # --- Parameters ---
    total_length = 120.0
    
    # Dimensions derived from fitting ~13 waveguides in 4um height
    wg_width = 0.15   
    gap = 0.1         
    pitch = wg_width + gap
    
    # Define the cross-section with relaxed bend radius constraint.
    # setting radius_min=0.1 allows the tight 0.5um bends required by the dense packing.
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius_min=0.1)

    # --- 1. Center Bundle ---
    # 5 parallel straight lines centered at Y=0
    n_center_lines = 5
    
    for i in range(n_center_lines):
        # Calculate y-offset to center the group
        y_loc = (i - (n_center_lines - 1) / 2) * pitch
        
        # Create and place straight waveguide
        wg = c << gf.components.straight(length=total_length, cross_section=xs)
        wg.y = y_loc

    # --- 2. Top Bundle ---
    # 4 concentric lines that bend UP at the ends
    n_outer_lines = 4
    
    # Calculate Y position of the top-most line of the center bundle
    y_center_top_limit = ((n_center_lines - 1) / 2) * pitch
    # Start the top bundle one pitch step above that
    y_start_top = y_center_top_limit + pitch
    
    # Base radius for the innermost bend
    r_min = 0.5

    for i in range(n_outer_lines):
        # Determine radius and position for concentricity
        radius = r_min + i * pitch
        y_loc = y_start_top + i * pitch
        
        # Calculate straight length so the total X-width remains total_length
        l_straight = total_length - 2 * radius
        
        # Create primitives
        bend = gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
        straight = gf.components.straight(length=l_straight, cross_section=xs)
        
        # Place the middle straight section
        s_ref = c << straight
        s_ref.x = 0
        s_ref.y = y_loc
        
        # Connect Right Bend (Straight East -> Curve Up)
        b_right = c << bend
        b_right.connect("o1", s_ref.ports["o2"])
        
        # Connect Left Bend (Straight West -> Curve Up)
        # We need to mirror the bend across the Vertical axis (flip X) 
        # so it faces East but still curves North.
        b_left = c << bend
        b_left.mirror(p1=(0,0), p2=(0,1)) # Mirror across Y-axis
        b_left.connect("o1", s_ref.ports["o1"])

    # --- 3. Bottom Bundle ---
    # 4 concentric lines that bend DOWN at the ends
    
    for i in range(n_outer_lines):
        radius = r_min + i * pitch
        # Mirror the Y location relative to center
        y_loc = -(y_start_top + i * pitch)
        l_straight = total_length - 2 * radius
        
        bend = gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
        straight = gf.components.straight(length=l_straight, cross_section=xs)
        
        # Place straight section
        s_ref = c << straight
        s_ref.x = 0
        s_ref.y = y_loc
        
        # Right Bend (Straight East -> Curve Down)
        # Mirror standard bend across Horizontal axis (flip Y).
        b_right = c << bend
        b_right.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis
        b_right.connect("o1", s_ref.ports["o2"])
        
        # Left Bend (Straight West -> Curve Down)
        # Rotate standard bend 180 degrees.
        b_left = c << bend
        b_left.rotate(180)
        b_left.connect("o1", s_ref.ports["o1"])

    return c

if __name__ == "__main__":
    # Generate the device
    device = parametric_device()
    
    # Save the GDS file
    gds_path = "parametric_device.gds"
    device.write_gds(gds_path)
    print(f"GDS file successfully written to: {gds_path}")
    
    # Optional: View the device if in a supported environment
    try:
        device.show()
    except:
        pass