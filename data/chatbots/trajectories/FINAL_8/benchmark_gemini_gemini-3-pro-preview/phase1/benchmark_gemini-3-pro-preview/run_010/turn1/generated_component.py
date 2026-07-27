import gdsfactory as gf

@gf.cell
def device_dense_coupler_array(
    length: float = 120.0,
    height: float = 4.0,
    w_wg: float = 0.15,
    g_wg: float = 0.1,
    bend_length: float = 25.0,
) -> gf.Component:
    """
    Creates a dense waveguide coupler array based on the provided image.
    Features a central straight bundle and flared outer bundles with thick caps.
    """
    c = gf.Component()
    
    # Derived parameters
    straight_section_length = length - 2 * bend_length
    pitch = w_wg + g_wg
    xs_std = gf.cross_section.cross_section(width=w_wg, layer=(1, 0))
    
    # -----------------------------------------------------------
    # 1. Center Bundle (5 Straight Waveguides)
    # -----------------------------------------------------------
    # These run the full length of the device and are centered at Y=0
    n_center = 5
    # Calculate indices to center around 0 (e.g., -2, -1, 0, 1, 2)
    indices = range(-(n_center//2), n_center//2 + 1)
    
    for i in indices:
        y_pos = i * pitch
        wg = c << gf.components.straight(length=length, cross_section=xs_std)
        # Center the waveguide. straight() creates a horizontal wg from (0,0) to (L,0).
        # We center it at (0, y_pos).
        wg.center = (0, y_pos)

    # -----------------------------------------------------------
    # 2. Flared Outer Regions (Top and Bottom)
    # -----------------------------------------------------------
    
    # Parameters estimated from image features
    gap_center_to_flare = 0.15
    # Start Y for the first flared line (relative to center bundle)
    y_flare_inner_top = (n_center // 2) * pitch + w_wg/2 + gap_center_to_flare + w_wg/2
    
    # Vertical flare offset (how much the outer lines bend away from center at the ends)
    dy_flare = 0.8
    n_flare_thin = 3  # Number of thin waveguides in the flared section
    w_cap = 0.7       # Width of the thick outer block
    
    def add_flared_row(y_straight_center, is_top=True, is_thick=False):
        """
        Helper to add a 'Bend-Straight-Bend' row.
        y_straight_center: The y-coordinate of the middle straight section.
        """
        width = w_cap if is_thick else w_wg
        xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
        
        # Calculate bend offset
        # If is_top=True:  Left part bends DOWN from high to y_straight.
        #                  Right part bends UP from y_straight to high.
        # bend_s(size=(L, h)) goes from (0,0) to (L, h).
        
        offset_y = -dy_flare if is_top else dy_flare
        
        # 1. Left Bend
        # For Top: We want to end at (x_straight_start, y_straight_center).
        # The bend has height 'offset_y'. 
        # So it starts at y_straight_center - offset_y.
        # wait: if offset_y is negative (top), -offset_y is positive (higher). Correct.
        
        b_l = c << gf.components.bend_s(size=(bend_length, offset_y), cross_section=xs)
        
        # Calculate Start Position
        # The Straight section is centered at x=0, so it starts at -straight_section_length/2.
        # The bend connects to the start of the straight section.
        # Bend End (port o2) must be at (-straight_section_length/2, y_straight_center)
        # bend_s moves from (0,0) to (L, h).
        # So Origin = Desired_End - (L, h)
        
        x_start = -straight_section_length/2 - bend_length
        y_start = y_straight_center - offset_y
        
        b_l.move((x_start, y_start))
        
        # 2. Straight Section
        st = c << gf.components.straight(length=straight_section_length, cross_section=xs)
        st.connect("o1", b_l.ports["o2"])
        
        # 3. Right Bend
        # For Top: Starts at y_straight, goes UP (positive dy).
        # We just invert the offset_y used for the left side.
        b_r = c << gf.components.bend_s(size=(bend_length, -offset_y), cross_section=xs)
        b_r.connect("o1", st.ports["o2"])

    # --- Generate Top Lines ---
    for i in range(n_flare_thin):
        y = y_flare_inner_top + i * pitch
        add_flared_row(y, is_top=True, is_thick=False)
        
    # --- Generate Top Thick Cap ---
    y_last_thin = y_flare_inner_top + (n_flare_thin - 1) * pitch
    y_cap_top = y_last_thin + w_wg/2 + g_wg + w_cap/2
    add_flared_row(y_cap_top, is_top=True, is_thick=True)
    
    # --- Generate Bottom Lines (Mirrored) ---
    y_flare_inner_bot = -y_flare_inner_top
    for i in range(n_flare_thin):
        y = y_flare_inner_bot - i * pitch
        add_flared_row(y, is_top=False, is_thick=False)

    # --- Generate Bottom Thick Cap ---
    y_last_thin_bot = y_flare_inner_bot - (n_flare_thin - 1) * pitch
    y_cap_bot = y_last_thin_bot - w_wg/2 - g_wg - w_cap/2
    add_flared_row(y_cap_bot, is_top=False, is_thick=True)

    return c

# Create and save the component
if __name__ == "__main__":
    device = device_dense_coupler_array()
    device.write_gds("dense_coupler_array.gds")
    device.show()