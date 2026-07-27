import gdsfactory as gf

@gf.cell
def coupler_directional():
    c = gf.Component()
    
    # --- Dimensions & Constants ---
    # Target footprint: 18.0 um x 3.0 um
    total_length = 18.0
    
    # Length Distribution
    # A 6:6:6 ratio creates the smooth, elongated look of the target image.
    l_coupler = 6.0
    l_bend = (total_length - l_coupler) / 2  # 6.0 um
    
    # Vertical Geometry
    # Footprint height 3.0um implies outer edges at y = +/- 1.5um.
    # For 0.5um width, the port centers are at +/- 1.25um.
    y_port = 1.25
    
    # Coupling region: Gap 0.2um centered at y=0.
    # Waveguide centers at +/- (0.1 + 0.25) = +/- 0.35um.
    y_coup = 0.35
    
    # Vertical shift required for S-bends
    dy = y_port - y_coup  # 0.9 um
    
    # Cross-section
    # Explicitly set radius=5.0 to prevent ValueError (calculated bend radius is ~7.7um).
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, radius=5.0)

    # --- 1. Central Straight Coupler ---
    coupler = c << gf.components.coupler_straight(
        length=l_coupler, 
        gap=0.2, 
        cross_section=xs
    )

    # --- 2. Robust Port Identification ---
    # We retrieve ports safely (compatible with recent GDSFactory versions)
    # and sort them spatially to ensure correct topology (no crossings).
    
    # Get all ports from the coupler reference
    all_ports = [coupler.ports[name] for name in coupler.ports]
    
    # Identify Inputs (West/Left) and Outputs (East/Right) based on x-coordinate
    coupler_center_x = coupler.x
    ports_in = [p for p in all_ports if p.center[0] < coupler_center_x]
    ports_out = [p for p in all_ports if p.center[0] > coupler_center_x]
    
    # Sort by Y-coordinate to identify Top and Bottom
    # Index 0 will be Bottom (lower Y), Index 1 will be Top (higher Y)
    ports_in.sort(key=lambda p: p.center[1])
    ports_out.sort(key=lambda p: p.center[1])
    
    in_bot = ports_in[0]
    in_top = ports_in[1]
    out_bot = ports_out[0]
    out_top = ports_out[1]

    # --- 3. Input S-Bends (Left Side) ---
    # We connect the "o2" port of the S-bend to the coupler input.
    # The bend calculates 'dy' from start (o1) to end (o2).
    # Since we work backwards from o2 (Coupler) to o1 (Port), we invert logic or check coords.
    
    # Top Left: Connects Port (y=1.25) to Coupler (y=0.35).
    # Bend goes from High to Low. dy = 0.35 - 1.25 = -0.9.
    bend_tl = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    bend_tl.connect("o2", in_top)
    
    # Bottom Left: Connects Port (y=-1.25) to Coupler (y=-0.35).
    # Bend goes from Low to High (less negative). dy = -0.35 - (-1.25) = +0.9.
    bend_bl = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    bend_bl.connect("o2", in_bot)

    # --- 4. Output S-Bends (Right Side) ---
    # We connect the "o1" port of the S-bend to the coupler output.
    # Bend goes from Coupler (o1) to Port (o2).
    
    # Top Right: Connects Coupler (y=0.35) to Port (y=1.25).
    # Bend goes from Low to High. dy = 1.25 - 0.35 = +0.9.
    bend_tr = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs)
    bend_tr.connect("o1", out_top)
    
    # Bottom Right: Connects Coupler (y=-0.35) to Port (y=-1.25).
    # Bend goes from High (less negative) to Low. dy = -1.25 - (-0.35) = -0.9.
    bend_br = c << gf.components.bend_s(size=(l_bend, -dy), cross_section=xs)
    bend_br.connect("o1", out_bot)

    # --- 5. Expose Ports ---
    c.add_port("o1", port=bend_tl.ports["o1"])
    c.add_port("o2", port=bend_bl.ports["o1"])
    c.add_port("o3", port=bend_tr.ports["o2"])
    c.add_port("o4", port=bend_br.ports["o2"])

    return c

# Create and save the device
device = coupler_directional()
device.write_gds("coupler_directional.gds")