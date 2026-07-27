import gdsfactory as gf

@gf.cell
def recreated_device_geometry():
    """
    Recreates the geometry from the provided image using parametric primitives.
    Footprint: 120.0 um (width) x 4.0 um (height).
    """
    c = gf.Component("recreated_device")

    # --- Constants & Dimensions ---
    W_TOTAL = 120.0
    H_TOTAL = 4.0
    
    # Layer definition
    layer = (1, 0)
    
    # Line widths (sub-micron for photonics look)
    thin_width = 0.08
    thick_width = 0.25
    spacing = 0.25 # Center-to-center spacing for grating lines
    
    # Cross-sections
    xs_thin = gf.cross_section.cross_section(width=thin_width, layer=layer)
    xs_thick = gf.cross_section.cross_section(width=thick_width, layer=layer)

    # --- 1. CENTRAL GRATING SECTION ---
    # 5 thin lines centered horizontally and vertically
    for i in range(-2, 3):
        y_pos = i * spacing
        line = c << gf.components.straight(length=W_TOTAL, cross_section=xs_thin)
        line.center = (0, y_pos)

    # --- 2. TOP AND BOTTOM SYMMETRIC BLOCKS ---
    def add_outer_block(is_top=True):
        y_sign = 1 if is_top else -1
        block_w = 90.0  # Slightly shorter than central grating
        base_y = y_sign * 1.0 # Starting vertical offset from center
        
        # A. Horizontal Bars (1 thick + 4 thin)
        # Thick base bar
        thick_bar = c << gf.components.straight(length=block_w, cross_section=xs_thick)
        thick_bar.center = (0, base_y)
        
        # 4 thin bars stacked outwards
        for i in range(1, 5):
            y_bar = base_y + (y_sign * i * spacing)
            thin_bar = c << gf.components.straight(length=block_w, cross_section=xs_thin)
            thin_bar.center = (0, y_bar)
            
        # B. Curved Side Rails (Dual-rail "arms")
        # Define an arc path that flares outwards
        rail_path = gf.path.arc(radius=10, angle=y_sign * 15)
        
        # Place rails on left (-1) and right (1) sides
        for x_sign in [-1, 1]:
            # Each arm consists of two parallel curved lines (dual-rail)
            for rail_offset in [0, 0.25]:
                rail = c << gf.path.extrude(rail_path, cross_section=xs_thin)
                
                # Rotate path to align vertically with the bars
                # The arc starts at (0,0), we rotate and move it to the bar ends
                rail.rotate(y_sign * 90 + 90)
                if x_sign == 1:
                    rail.mirror_x()
                
                # Position the rail so it encloses the horizontal bars
                # Shifted slightly outside the block width
                start_x = x_sign * (block_w/2 + 0.5 + rail_offset)
                rail.move((start_x, base_y - y_sign * (thick_width/2)))

    # Generate top and bottom structures
    add_outer_block(is_top=True)
    add_outer_block(is_top=False)

    return c

if __name__ == "__main__":
    # Create the component
    component = recreated_device_geometry()
    
    # Save the GDS file
    component.write_gds("recreated_device.gds")
    
    # Optional: Display the component (requires a viewer like KLayout)
    # component.show()