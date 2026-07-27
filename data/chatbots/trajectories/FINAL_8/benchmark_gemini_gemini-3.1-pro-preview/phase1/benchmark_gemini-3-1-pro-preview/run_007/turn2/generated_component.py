import gdsfactory as gf

@gf.cell
def apodized_symmetric_coupler_fixed():
    """
    Creates the apodized symmetrical directional coupler that exactly matches the target geometry.
    It uses U-shaped outer waveguides that flare out towards the edges and are clipped 
    by a boolean bounding box.
    """
    c = gf.Component("apodized_symmetric_coupler_fixed")
    wg_group = gf.Component("wg_group")

    # Target footprint constraints
    L_total = 120.0
    total_height = 4.0

    # Routing and geometric parameters
    L_straight_center = 50.0  # The flat central coupling region
    dx = 25.0                 # X-length of the S-bends
    # The remaining length (120 - 50 - 50)/2 = 10um will be flat horizontal at the very edges
    L_straight_edge = (L_total - L_straight_center - 2 * dx) / 2.0 
    
    w_thin = 0.08  # Width of standard waveguides
    g = 0.06       # Gap between waveguides (white space)
    pitch = w_thin + g
    
    # Large vertical shift that pushes the outer groups to the top/bottom edges
    dy_shift_amount = 0.95 
    # Massive width for the top/bottom blocks to guarantee they fill the outer space before clipping
    W_thick = 3.0 

    # We add a slight overshoot to the paths before boolean clipping to prevent floating-point edge artifacts
    overshoot = 5.0 
    L_edge_extended = L_straight_edge + overshoot
    L_total_wg = L_straight_center + 2 * dx + 2 * L_edge_extended

    def add_waveguide_track(y_center, width, dy_shift):
        """
        Creates a symmetrical track.
        - In the middle (X=0), its Y coordinate is `y_center`.
        - At the far left/right edges, its Y coordinate flares out to `y_center + dy_shift`.
        """
        xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

        if dy_shift == 0.0:
            # 1. Perfectly straight lines for the center group
            str_comp = gf.components.straight(length=L_total_wg, cross_section=xs)
            ref = wg_group << str_comp
            ref.move((-L_total_wg / 2, y_center))
        else:
            # 2. U-shaped paths for the outer groups
            
            # Left edge (straight)
            edge_left = wg_group << gf.components.straight(length=L_edge_extended, cross_section=xs)
            edge_left.move((-L_total_wg / 2, y_center + dy_shift))
            
            # Left S-bend (bends from edge Y back to center Y)
            bend_left = wg_group << gf.components.bend_s(size=(dx, -dy_shift), cross_section=xs)
            bend_left.connect('o1', edge_left.ports['o2'])
            
            # Center (straight coupling region)
            center_straight = wg_group << gf.components.straight(length=L_straight_center, cross_section=xs)
            center_straight.connect('o1', bend_left.ports['o2'])
            
            # Right S-bend (bends from center Y out to edge Y)
            bend_right = wg_group << gf.components.bend_s(size=(dx, dy_shift), cross_section=xs)
            bend_right.connect('o1', center_straight.ports['o2'])
            
            # Right edge (straight)
            edge_right = wg_group << gf.components.straight(length=L_edge_extended, cross_section=xs)
            edge_right.connect('o1', bend_right.ports['o2'])

    # --- Build the waveguiding array from center outwards ---
    
    # 1. Center Group: 5 perfectly straight thin waveguides
    for i in range(-2, 3):
        add_waveguide_track(i * pitch, w_thin, 0.0)

    # 2. Top Group: 4 thin U-shaped waveguides
    for i in range(3, 7):
        add_waveguide_track(i * pitch, w_thin, dy_shift_amount)
        
    # 3. Top Thick Block: 1 massive U-shaped waveguide
    # Calculate its center so its bottom edge maintains the exact gap 'g' above the 4th thin line
    y_top_outer_line = 6 * pitch
    y_top_thick_center = y_top_outer_line + (w_thin / 2) + g + (W_thick / 2)
    add_waveguide_track(y_top_thick_center, W_thick, dy_shift_amount)

    # 4. Bottom Group: 4 thin U-shaped waveguides
    for i in range(3, 7):
        add_waveguide_track(-i * pitch, w_thin, -dy_shift_amount)
        
    # 5. Bottom Thick Block: 1 massive U-shaped waveguide
    y_bottom_outer_line = -6 * pitch
    y_bottom_thick_center = y_bottom_outer_line - (w_thin / 2) - g - (W_thick / 2)
    add_waveguide_track(y_bottom_thick_center, W_thick, -dy_shift_amount)

    # --- Apply Bounding Box Clipping ---
    
    # The true geometry is formed by clipping the oversized U-shapes with the 120x4 boundary.
    # This naturally produces the thick middle/thin edge features of the solid blocks.
    bbox = gf.components.rectangle(size=(L_total, total_height), layer=(1, 0), centered=True)
    
    # Intersect the continuous waveguide group with the precise rectangular bounds
    final_geometry = gf.boolean(A=wg_group, B=bbox, operation="and", layer=(1, 0))
    c << final_geometry

    return c

if __name__ == "__main__":
    # Generate the component and write it to a GDS file
    c = apodized_symmetric_coupler_fixed()
    c.write_gds("apodized_symmetric_coupler_fixed.gds")