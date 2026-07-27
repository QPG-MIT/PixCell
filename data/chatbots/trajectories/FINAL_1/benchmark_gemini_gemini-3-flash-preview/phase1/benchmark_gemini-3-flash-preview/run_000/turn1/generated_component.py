import gdsfactory as gf

@gf.cell
def trident_edge_coupler():
    """
    Recreates the trident edge coupler geometry from the reference image.
    Target Footprint: 40.0 um x 1.7 um
    """
    c = gf.Component("trident_coupler")
    
    # Footprint and Layer Constraints
    total_length = 40.0
    total_width = 1.7
    layer = (1, 0)
    
    # Parametric waveguide widths
    w_center_in = 0.5    # Center waveguide input width
    w_side = 0.35        # Side arm width
    gap_start = 0.08     # Initial gap between center and sides
    
    # 1. Define Cross Section (Reference Catalog Section 6 syntax)
    # Using the exact syntax from the catalog example to avoid TypeErrors
    xs_side = gf.cross_section.cross_section(width=w_side, layer=layer)
    
    # 2. Central Taper
    # The center waveguide tapers to a point to transfer the optical mode
    taper_length = 30.0  # Occupies most of the device length
    center_taper = c << gf.components.taper(
        length=taper_length, 
        width1=w_center_in, 
        width2=0.02, 
        layer=layer
    )
    center_taper.movex(0)
    
    # 3. Symmetric Side Arms (Top and Bottom)
    # Calculation for vertical divergence to match 1.7um footprint
    # Initial center-to-center offset: (center_width/2) + gap + (side_width/2)
    y_init = (w_center_in / 2) + gap_start + (w_side / 2)
    # Final center-to-center offset to hit 1.7um edge: (total_width/2) - (side_width/2)
    y_final = (total_width / 2) - (w_side / 2)
    dy = y_final - y_init
    
    # Length allocation for side arms to total 40um
    side_straight_len = 15.0
    side_bend_len = total_length - side_straight_len
    
    for sign in [+1, -1]:
        # Straight parallel section
        straight = c << gf.components.straight(
            length=side_straight_len, 
            cross_section=xs_side
        )
        straight.move((0, sign * y_init))
        
        # S-bend flare section
        # size parameter is (dx, dy)
        sbend = c << gf.components.bend_s(
            size=(side_bend_len, sign * dy), 
            cross_section=xs_side
        )
        # Connect to the straight segment's output port
        sbend.connect("o1", straight.ports["o2"])
        
    return c

if __name__ == "__main__":
    # Instantiate the component
    component = trident_edge_coupler()
    
    # Verify Footprint using safe property access
    width = component.xsize
    height = component.ysize
    
    print(f"Geometry created successfully.")
    print(f"Dimensions: {width:.2f} um (L) x {height:.2f} um (W)")
    
    # Show in layout viewer
    component.show()