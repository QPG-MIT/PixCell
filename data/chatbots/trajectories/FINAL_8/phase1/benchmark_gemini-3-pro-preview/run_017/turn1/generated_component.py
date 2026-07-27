import gdsfactory as gf

@gf.cell
def device_reconstruction():
    """
    Reconstruction of the 120x4um waveguide array device.
    Consists of a central straight bundle flanked by two bent/flared bundles.
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    # Constraints
    length_total = 120.0
    
    # Waveguide dimensions (tuned to fit 4um height limit)
    wg_width = 0.15
    gap = 0.1
    pitch = wg_width + gap
    
    # Longitudinal dimensions
    # The device has a long central straight section and short bends at ends
    length_bend = 20.0
    length_straight = length_total - (2 * length_bend) # 80.0
    
    # Vertical flare dimensions
    # How much the outer bundles move vertically
    dy_flare = 0.7 
    
    # Cross section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Central Bundle ---
    # 5 straight parallel lines centered at y=0
    num_center_lines = 5
    
    for i in range(num_center_lines):
        # Calculate y-offset to center the group
        y = (i - (num_center_lines - 1) / 2) * pitch
        
        wg = c << gf.components.straight(length=length_total, cross_section=xs)
        wg.y = y

    # --- 2. Define the "Bent" Line Primitive ---
    # Helper to create one line of the outer bundles: S-bend down -> Straight -> S-bend up
    def create_bent_line():
        cmp = gf.Component()
        
        # Left S-bend (Bringing waveguide IN towards center)
        # Note: bend_s goes from (0,0) to (x,y). We want to drop down by dy_flare.
        b_in = cmp << gf.components.bend_s(
            size=(length_bend, -dy_flare), 
            cross_section=xs
        )
        
        # Middle Straight Section
        st = cmp << gf.components.straight(length=length_straight, cross_section=xs)
        st.connect("o1", b_in.ports["o2"])
        
        # Right S-bend (Taking waveguide OUT away from center)
        b_out = cmp << gf.components.bend_s(
            size=(length_bend, dy_flare), 
            cross_section=xs
        )
        b_out.connect("o1", st.ports["o2"])
        
        # Expose ports for reference
        cmp.add_port("o1", port=b_in.ports["o1"])
        return cmp

    # Create the template component
    bent_line_template = create_bent_line()

    # --- 3. Place Top Flanking Bundle ---
    # 3 lines that sit above the central bundle
    num_outer_lines = 3
    
    # Gap between the central bundle and the flanking bundles
    interaction_gap = 0.25
    
    # Calculate where the lowest line of the top bundle sits in the straight region
    # Center bundle top edge roughly at: 2 * pitch
    y_center_top_edge = ((num_center_lines - 1) / 2) * pitch
    y_straight_start_top = y_center_top_edge + interaction_gap + (wg_width/2)

    for i in range(num_outer_lines):
        # Target Y position for the straight section of this line
        y_target_straight = y_straight_start_top + (i * pitch)
        
        ref = c << bent_line_template
        # The template starts at (0,0) and drops by dy_flare to reach the straight part.
        # To align the straight part to y_target_straight, the start (o1) must be higher.
        ref.y = y_target_straight + dy_flare
        ref.x = 0

    # --- 4. Place Bottom Flanking Bundle ---
    # 3 lines mirrored below
    for i in range(num_outer_lines):
        # Target Y position for the straight section (negative)
        y_target_straight = -(y_straight_start_top + (i * pitch))
        
        ref = c << bent_line_template
        ref.mirror_y() # Flips the S-bends so it becomes Up -> Straight -> Down
        
        # Adjust position. 
        # After mirroring, a drop of -dy_flare becomes a rise of +dy_flare relative to origin.
        # We want the straight part at y_target_straight.
        # The origin needs to be lower than the straight part.
        ref.y = y_target_straight - dy_flare
        ref.x = 0

    return c

# Generate and Export
device = device_reconstruction()
device.write_gds("reconstructed_device.gds")

# Optional: Visualize if running in a notebook
# device.plot()