import gdsfactory as gf

@gf.cell
def device_recreation():
    c = gf.Component()
    
    # 1. Define Design Parameters based on Footprint (18x3)
    # The device is 18um long and 3um high.
    length = 18.0
    height = 3.0
    
    # Standard waveguide width for silicon photonics
    wg_width = 0.5
    
    # Create the cross-section
    xs = gf.cross_section.cross_section(width=wg_width)
    
    # 2. Calculate Coordinates
    # We assume the 3um height defines the outer bounding box.
    # Top WG outer edge: y = 1.5
    # Bottom WG outer edge: y = -1.5
    # Therefore, starting center y-positions (ports):
    y_start_top = 1.5 - wg_width/2  # 1.25
    y_start_bot = -1.5 + wg_width/2 # -1.25
    
    # Define the narrowest gap in the middle.
    # Visually, the gap is distinct but small (coupling region).
    gap_min = 0.2
    y_mid_top = gap_min/2 + wg_width/2  # 0.35
    y_mid_bot = -y_mid_top              # -0.35
    
    # The device is symmetric, split length into two halves
    half_length = length / 2
    
    # Calculate the vertical shift (dy) for the S-bends
    # Top-Left: Goes down from 1.25 to 0.35
    dy_top_converge = y_mid_top - y_start_top # -0.9
    
    # Top-Right: Goes up from 0.35 to 1.25
    dy_top_diverge = y_start_top - y_mid_top  # 0.9
    
    # Bottom-Left: Goes up from -1.25 to -0.35
    dy_bot_converge = y_mid_bot - y_start_bot # 0.9
    
    # Bottom-Right: Goes down from -0.35 to -1.25
    dy_bot_diverge = y_start_bot - y_mid_bot  # -0.9
    
    # 3. Construct Geometry using Primitives (bend_s)
    
    # --- Top Arm ---
    # Top-Left S-bend
    tl = c << gf.components.bend_s(
        size=(half_length, dy_top_converge), 
        cross_section=xs
    )
    # Move start point to input position. bend_s starts at (0,0) by default.
    tl.move((0, y_start_top))
    
    # Top-Right S-bend
    tr = c << gf.components.bend_s(
        size=(half_length, dy_top_diverge), 
        cross_section=xs
    )
    # Connect start of tr to end of tl
    tr.connect("o1", tl.ports["o2"])
    
    # --- Bottom Arm ---
    # Bottom-Left S-bend
    bl = c << gf.components.bend_s(
        size=(half_length, dy_bot_converge), 
        cross_section=xs
    )
    bl.move((0, y_start_bot))
    
    # Bottom-Right S-bend
    br = c << gf.components.bend_s(
        size=(half_length, dy_bot_diverge), 
        cross_section=xs
    )
    br.connect("o1", bl.ports["o2"])
    
    # 4. Expose Ports
    c.add_port("o1", port=tl.ports["o1"]) # Top Input
    c.add_port("o2", port=bl.ports["o1"]) # Bottom Input
    c.add_port("o3", port=tr.ports["o2"]) # Top Output
    c.add_port("o4", port=br.ports["o2"]) # Bottom Output
    
    return c

# Create the device
device = device_recreation()

# Save GDS
device.write_gds("device_recreation.gds")