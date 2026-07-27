import gdsfactory as gf

@gf.cell
def mode_converter_structure():
    c = gf.Component("main")
    
    # Raw component to build un-cropped traces
    raw = gf.Component("raw_geom")
    
    # --- Layout & Routing Parameters ---
    # Widths must be multiples of 2 dbu (0.002) to satisfy symmetrical validation.
    L_total = 120.0
    L_straight = 50.0  # Length of the central straight section
    L_bend = (L_total - L_straight) / 2.0
    
    # Component Thicknesses (Clean multiples of 0.002)
    w_thin = 0.032
    w_inner = 0.200
    w_outer = 0.800
    
    # Spacing Parameters
    gap_thin = 0.040
    pitch = w_thin + gap_thin
    gap_group = 0.080  # Wider gap separating the major groups
    
    # How much the outer branches deflect up/down vertically at the edges
    dy_flare = 0.700 
    
    # --- 1. Central Straight Tracks ---
    # 5 continuous thin lines running entirely straight down the center
    xs_thin = gf.cross_section.cross_section(width=w_thin, layer=(1, 0))
    for i in range(-2, 3):
        y = i * pitch
        st = gf.components.straight(length=L_total, cross_section=xs_thin)
        ref = raw << st
        ref.move((-L_total / 2.0, y))

    # --- 2. Helper Function for Flared Branches ---
    def add_flare(width, y_mid, dy):
        """Builds a symmetrical flared waveguide that bends vertically outwards at the edges."""
        xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
        
        # Central straight segment
        st = gf.components.straight(length=L_straight, cross_section=xs)
        st_ref = raw << st
        st_ref.move((-L_straight / 2.0, y_mid))
        
        # Left outward bend (flares towards the left edge)
        b_left = gf.components.bend_s(size=(L_bend, -dy), cross_section=xs)
        bl_ref = raw << b_left
        bl_ref.connect("o2", st_ref.ports["o1"])
        
        # Right outward bend (flares towards the right edge)
        b_right = gf.components.bend_s(size=(L_bend, dy), cross_section=xs)
        br_ref = raw << b_right
        br_ref.connect("o1", st_ref.ports["o2"])

    # --- 3. Compute Precise Y Coordinates ---
    # Top of the central 5-straight group
    top_of_center = 2 * pitch + w_thin / 2.0
    
    # Inner thick band
    y_inner = top_of_center + gap_group + w_inner / 2.0
    top_of_inner = y_inner + w_inner / 2.0
    
    # 4 intermediate thin flaring tracks
    y_thins = [top_of_inner + gap_group + w_thin / 2.0 + i * pitch for i in range(4)]
    top_of_thins = y_thins[-1] + w_thin / 2.0
    
    # Outer thick block
    y_outer = top_of_thins + gap_group + w_outer / 2.0
    
    # --- 4. Assemble Top and Bottom Symmetric Sections ---
    # Top Half (Positive Y, positive dy deflection)
    add_flare(w_inner, y_inner, dy_flare)
    for yt in y_thins:
        add_flare(w_thin, yt, dy_flare)
    add_flare(w_outer, y_outer, dy_flare)
    
    # Bottom Half (Negative Y, negative dy deflection)
    add_flare(w_inner, -y_inner, -dy_flare)
    for yt in y_thins:
        add_flare(w_thin, -yt, -dy_flare)
    add_flare(w_outer, -y_outer, -dy_flare)

    # --- 5. Enforce Precise Footprint Cropping ---
    # Crops the flaring outermost structures exactly at the [-2.0, +2.0] Y-boundary. 
    # This naturally forms the bold, flat cutoffs at the corners just like the original image.
    bbox = gf.components.rectangle(size=(120.0, 4.0), layer=(1, 0), centered=True)
    final_geom = gf.boolean(A=raw, B=bbox, operation="and", layer=(1, 0))
    
    c << final_geom
    return c


if __name__ == "__main__":
    # Create the structure and save the actual GDS file
    device = mode_converter_structure()
    device.write_gds("device.gds")
    device.show()