import gdsfactory as gf

@gf.cell
def coupler_directional():
    c = gf.Component()
    
    # --- Dimensions & Constants ---
    total_length = 18.0
    
    # Waveguide cross-section
    # We define a custom cross-section with a smaller minimum bend radius (5.0um).
    # The default is often 10.0um, which triggers errors for compact devices like this
    # (footprint height 3um implies vertical shifts that require tighter bends).
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, radius=5.0)
    
    # Geometry parameters
    # Adjusted Ratios:
    # The straight coupling region is set to 4.0um.
    # The remaining 14.0um is split between the two S-bends (7.0um each).
    # This 7:4:7 ratio produces the smoother, more elongated curves seen in the original image,
    # compared to a 1:1:1 ratio which looks more compressed.
    gap = 0.2                     
    l_coupler = 4.0               
    l_bend = (total_length - l_coupler) / 2  # 7.0 um
    
    # Vertical Positions (relative to center y=0)
    # The footprint height is 3.0um. For 0.5um waveguides, the outer edges touch y=+/-1.5.
    # Therefore, the center lines of the input/output ports are at +/- 1.25.
    y_port_top = 1.25             
    
    # For the coupling region, gap is 0.2um.
    # Center lines are at +/- (gap/2 + width/2) = +/- 0.35.
    y_coupler_top = 0.35          
    
    # Calculate the vertical shift (dy) required for the S-bends
    dy = y_port_top - y_coupler_top # 0.9 um

    # --- 1. Central Coupling Region ---
    # Creates two parallel straight waveguides centered at y=+/- 0.35
    coupler = c << gf.components.coupler_straight(
        length=l_coupler, 
        gap=gap, 
        cross_section=xs
    )

    # --- 2. Input S-Bends (Left Side) ---
    # Top Left: Connects high input port (y=1.25) to lower coupler port (y=0.35)
    # The bend travels distance 'l_bend' in X, and '-dy' in Y.
    bend_tl = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    bend_tl.connect("o2", coupler.ports["o1"])
    
    # Bottom Left: Connects low input port (y=-1.25) to higher coupler port (y=-0.35)
    # The bend travels distance 'l_bend' in X, and '+dy' in Y.
    bend_bl = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    bend_bl.connect("o2", coupler.ports["o2"])

    # --- 3. Output S-Bends (Right Side) ---
    # Top Right: Connects lower coupler port (y=0.35) to higher output port (y=1.25)
    # The bend travels '+dy' in Y.
    bend_tr = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    bend_tr.connect("o1", coupler.ports["o3"])
    
    # Bottom Right: Connects higher coupler port (y=-0.35) to lower output port (y=-1.25)
    # The bend travels '-dy' in Y.
    bend_br = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    bend_br.connect("o1", coupler.ports["o4"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=bend_tl.ports["o1"])
    c.add_port("o2", port=bend_bl.ports["o1"])
    c.add_port("o3", port=bend_tr.ports["o2"])
    c.add_port("o4", port=bend_br.ports["o2"])

    return c

# Create and save the device
device = coupler_directional()
device.write_gds("coupler_directional.gds")