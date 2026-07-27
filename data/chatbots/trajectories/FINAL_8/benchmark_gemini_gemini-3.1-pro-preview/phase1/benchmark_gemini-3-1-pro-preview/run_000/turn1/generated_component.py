import gdsfactory as gf

@gf.cell
def multi_waveguide_coupler() -> gf.Component:
    """
    Recreates the symmetric 3-group multi-waveguide directional coupler.
    The structure consists of a central straight bus of 5 waveguides, 
    flanked by top and bottom 5-waveguide buses that S-bend in to couple.
    The entire design is scaled to perfectly match the 120.0 x 4.0 um footprint.
    """
    c = gf.Component("multi_waveguide_coupler")

    # --- 1. Footprint Constraints ---
    L_total = 120.0
    H_total = 4.0
    
    # --- 2. Longitudinal Dimensions ---
    L_couple = 60.0  # Length of the central straight coupling region
    dx = (L_total - L_couple) / 2.0  # X-distance allocated for S-bends (30.0 um)
    
    # --- 3. Transverse Geometry ---
    # The structure visually merges into 15 uniformly spaced waveguides in the center.
    # We calibrate width and gap to occupy about half the height in the coupling region.
    wg_width = 0.08
    wg_gap = 0.06
    pitch = wg_width + wg_gap  # 0.14 um
    
    # Single waveguide standard cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Port positions (Y-coordinates at the extreme left/right edges)
    # We strictly enforce the outermost waveguides to touch the bounding box (Y = ±2.0)
    y_top_port_max = (H_total / 2.0) - (wg_width / 2.0)
    y_bot_port_min = -(H_total / 2.0) + (wg_width / 2.0)
    
    # --- 4. Assembly ---
    # We iterate over 15 waveguide indices (from -7 to +7)
    for i in range(-7, 8):
        
        if -2 <= i <= 2:
            # --- CENTRAL GROUP ---
            # 5 perfectly straight lines passing through the entire length
            wg = c << gf.components.straight(length=L_total, cross_section=xs)
            wg.move((-L_total / 2.0, i * pitch))
            
        elif i >= 3:
            # --- TOP GROUP ---
            y_couple = i * pitch
            
            # Preserve the exact uniform spacing at the ports
            # i=7 is the uppermost waveguide, mapped to y_top_port_max
            y_port = y_top_port_max - (7 - i) * pitch
            
            # Vertical drop required by the S-bend (Negative value)
            dy = y_couple - y_port 
            
            # Assemble: Bend -> Straight -> Bend
            b1 = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
            str1 = c << gf.components.straight(length=L_couple, cross_section=xs)
            b2 = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
            
            # Move first bend to the left port, then daisy-chain connections
            b1.move((-L_total / 2.0, y_port))
            str1.connect("o1", b1.ports["o2"])
            b2.connect("o1", str1.ports["o2"])
            
        elif i <= -3:
            # --- BOTTOM GROUP ---
            y_couple = i * pitch
            
            # Preserve the exact uniform spacing at the ports
            # i=-7 is the lowermost waveguide, mapped to y_bot_port_min
            y_port = y_bot_port_min + (i - (-7)) * pitch
            
            # Vertical rise required by the S-bend (Positive value)
            dy = y_couple - y_port 
            
            # Assemble: Bend -> Straight -> Bend
            b1 = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
            str1 = c << gf.components.straight(length=L_couple, cross_section=xs)
            b2 = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
            
            # Move first bend to the left port, then daisy-chain connections
            b1.move((-L_total / 2.0, y_port))
            str1.connect("o1", b1.ports["o2"])
            b2.connect("o1", str1.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate and visualize the device
    device = multi_waveguide_coupler()
    device.show()