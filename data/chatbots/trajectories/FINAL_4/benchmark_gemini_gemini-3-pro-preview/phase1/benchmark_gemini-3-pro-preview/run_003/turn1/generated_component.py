import gdsfactory as gf

@gf.cell
def coupler_directional():
    c = gf.Component()
    
    # --- Dimensions & Constants ---
    total_length = 18.0
    
    # Waveguide cross-section
    # FIX: We explicitly set 'radius=5.0'. This lowers the minimum bend radius constraint
    # from the default 10.0um to 5.0um, allowing the ~7.6um bends required by the footprint.
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, radius=5.0)
    
    # Geometry parameters
    gap = 0.2                     # Gap between waveguides in the coupling region
    l_coupler = 6.0               # Length of the straight coupling region
    l_bend = (total_length - l_coupler) / 2  # Length of the S-bends (6.0 um)
    
    # Vertical Positions
    # Y-coordinates relative to center y=0
    # Outer ports are at +/- 1.25 (centers of waveguides at 3um total height limits)
    y_port_top = 1.25             
    # Coupling waveguides are at +/- 0.35 (0.1 gap half-width + 0.25 wg half-width)
    y_coupler_top = 0.35          
    
    # Calculate the vertical shift (dy) required for the S-bends
    dy = y_port_top - y_coupler_top # 0.9 um

    # --- 1. Central Coupling Region ---
    # Creates two parallel straight waveguides
    coupler = c << gf.components.coupler_straight(
        length=l_coupler, 
        gap=gap, 
        cross_section=xs
    )

    # --- 2. Input S-Bends (Left Side) ---
    # Top Left: Connects high input port to lower coupler port
    # Note: size=(x, y). Negative y means the bend goes "down".
    bend_tl = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    bend_tl.connect("o2", coupler.ports["o1"])
    
    # Bottom Left: Connects low input port to higher coupler port
    bend_bl = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    bend_bl.connect("o2", coupler.ports["o2"])

    # --- 3. Output S-Bends (Right Side) ---
    # Top Right: Connects lower coupler port to higher output port
    bend_tr = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    bend_tr.connect("o1", coupler.ports["o3"])
    
    # Bottom Right: Connects higher coupler port to lower output port
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

# Optional: Visualize
device.show()