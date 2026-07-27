import gdsfactory as gf

@gf.cell
def compact_modulator():
    """
    Recreates the compact racetrack MZI device based on the provided image
    and footprint constraints (3um x 5.5um).
    """
    c = gf.Component()
    
    # 1. Define Geometry Parameters
    # -----------------------------
    # Derived from footprint: 5.5um width, 3.0um height
    width = 0.4          # Waveguide width
    layer = (1, 0)       # Standard GDS layer
    
    # Outer ring dimensions
    h_total = 3.0
    l_total = 5.5
    r_outer = h_total / 2.0             # 1.5um
    r_center = r_outer - (width / 2.0)  # 1.3um
    l_straight = l_total - (2 * r_outer)# 2.5um
    
    # Inner arm dimensions
    y_inner_offset = 0.6
    pad_size = (0.7, 0.5)
    pad_gap = 0.2
    
    # FIX 1: CrossSection radius constraint
    # We define a custom cross_section with radius_min small enough 
    # to allow the 1.3um radius without raising a ValueError.
    xs = gf.cross_section.cross_section(
        width=width, 
        layer=layer, 
        radius=r_center,
        radius_min=0.5
    )

    # 2. Construct the Outer Racetrack
    # --------------------------------
    # Top Straight
    wg_top = c << gf.components.straight(length=l_straight, cross_section=xs)
    wg_top.movey(r_center)
    wg_top.movex(-l_straight/2)
    
    # Bottom Straight
    wg_bot = c << gf.components.straight(length=l_straight, cross_section=xs)
    wg_bot.movey(-r_center)
    wg_bot.movex(-l_straight/2)
    
    # Left Bend (180 degrees)
    bend_left = c << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs)
    bend_left.rotate(90)
    bend_left.movex(-l_straight/2)
    
    # Right Bend (180 degrees)
    bend_right = c << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs)
    bend_right.rotate(-90)
    bend_right.movex(l_straight/2)

    # 3. Construct the Inner MZI Arms
    # -------------------------------
    # Inner Top Arm
    inner_top = c << gf.components.straight(length=l_straight, cross_section=xs)
    inner_top.movey(y_inner_offset)
    inner_top.movex(-l_straight/2)
    
    # Inner Bottom Arm
    inner_bot = c << gf.components.straight(length=l_straight, cross_section=xs)
    inner_bot.movey(-y_inner_offset)
    inner_bot.movex(-l_straight/2)

    # 4. Construct the Transitions (Splitters)
    # ----------------------------------------
    # S-bends connect inner arms to the apex of the outer bends
    
    transition_length = r_center - (width/2)
    
    # Left Transitions
    # Connect s_bend to the left end of the inner straight. 
    # Connection logic automatically orients the s-bend outwards to the left.
    s_lt = c << gf.components.bend_s(
        size=(transition_length, -y_inner_offset), 
        cross_section=xs
    )
    s_lt.connect("o1", inner_top.ports["o1"])
    
    s_lb = c << gf.components.bend_s(
        size=(transition_length, y_inner_offset), 
        cross_section=xs
    )
    s_lb.connect("o1", inner_bot.ports["o1"])
    
    # Right Transitions
    # Connect s_bend to the right end of the inner straight.
    s_rt = c << gf.components.bend_s(
        size=(transition_length, -y_inner_offset), 
        cross_section=xs
    )
    s_rt.connect("o1", inner_top.ports["o2"])
    
    s_rb = c << gf.components.bend_s(
        size=(transition_length, y_inner_offset), 
        cross_section=xs
    )
    s_rb.connect("o1", inner_bot.ports["o2"])

    # 5. Add Heater/Contact Pads
    # --------------------------
    pad = gf.components.rectangle(size=pad_size, layer=layer, centered=True)
    x_offset_pad = pad_size[0]/2 + pad_gap/2
    
    # Top Pads
    p1 = c << pad; p1.move(( -x_offset_pad, y_inner_offset ))
    p2 = c << pad; p2.move(( x_offset_pad, y_inner_offset ))
    
    # Bottom Pads
    p3 = c << pad; p3.move(( -x_offset_pad, -y_inner_offset ))
    p4 = c << pad; p4.move(( x_offset_pad, -y_inner_offset ))

    # 6. Merge Geometries (FIXED)
    # ---------------------------
    # FIX 2: Use gf.boolean instead of gf.geometry.boolean
    # We pass 'c' as both operands to essentially flatten the component into a single polygon set.
    c_merged = gf.boolean(c, c, operation="or", layer=layer)
    
    return c_merged

if __name__ == "__main__":
    # Generate and save the device
    device = compact_modulator()
    device.show()
    device.write_gds("compact_modulator.gds")