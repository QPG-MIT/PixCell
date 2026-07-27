import gdsfactory as gf

@gf.cell
def adiabatic_mode_converter():
    """
    Recreates the adiabatic converter geometry from the image.
    Footprint target: 40.0 um x 1.7 um
    """
    c = gf.Component("adiabatic_mode_converter")
    
    # 1. Define Design Parameters
    # Total length = 40.0 um. We split this into a straight and a bending section.
    L_total = 40.0
    L_straight = 26.0
    L_bend = L_total - L_straight
    
    w_center_start = 0.4
    w_center_end = 0.01  # Narrows to a point
    w_side = 0.35
    gap_initial = 0.1
    
    # To reach a total height of 1.7um from an initial width of 1.3um:
    # Initial width = w_center_start + 2*gap_initial + 2*w_side = 0.4 + 0.2 + 0.7 = 1.3
    # Target height = 1.7. Shift per side = (1.7 - 1.3) / 2 = 0.2
    y_shift = 0.2 
    
    target_layer = (1, 0)
    
    # Define CrossSection for side waveguides (Catalog Section 6)
    xs_side = gf.cross_section.cross_section(width=w_side, layer=target_layer)

    # 2. Create Parametric Primitives (Catalog Section 1)
    
    # Central Tapered Waveguide
    center_taper = gf.components.taper(
        length=L_straight, 
        width1=w_center_start, 
        width2=w_center_end,
        layer=target_layer
    )
    
    # Side Waveguide Straight Segments
    side_straight = gf.components.straight(length=L_straight, cross_section=xs_side)
    
    # S-bends for the diverging arms. size=(dx, dy)
    side_s_bend_top = gf.components.bend_s(size=(L_bend, y_shift), cross_section=xs_side)
    side_s_bend_bot = gf.components.bend_s(size=(L_bend, -y_shift), cross_section=xs_side)

    # 3. Component Assembly (Catalog Section 6)
    
    # Add Center Taper
    ct_ref = c << center_taper
    
    # Calculate vertical center-to-center offset for side arms
    y_offset = (w_center_start / 2) + gap_initial + (w_side / 2)
    
    # Assemble Top Side Arm
    st_top = c << side_straight
    st_top.movey(y_offset)
    sb_top = c << side_s_bend_top
    sb_top.connect("o1", st_top.ports["o2"])
    
    # Assemble Bottom Side Arm
    st_bot = c << side_straight
    st_bot.movey(-y_offset)
    sb_bot = c << side_s_bend_bot
    sb_bot.connect("o1", st_bot.ports["o2"])

    # Center the device at (0,0) by moving it by the negative of its current center
    # This replaces the failing .align() method.
    c.move(-c.center)

    return c

if __name__ == "__main__":
    # Generate the component
    device = adiabatic_mode_converter()
    
    # Print footprint to verify constraints (40.0 x 1.7)
    bbox = device.bbox()
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    print(f"Verified Footprint: {width:.1f} um x {height:.1f} um")
    
    # View the result
    device.show()
    device.write_gds("adiabatic_converter.gds")