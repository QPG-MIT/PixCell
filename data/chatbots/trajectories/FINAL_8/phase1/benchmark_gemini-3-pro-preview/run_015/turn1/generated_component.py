import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Recreates the directional coupler from the image using parametric primitives.
    Constraint: 120um x 4um footprint.
    """
    c = gf.Component()
    
    # 1. Define Design Parameters
    total_length = 120.0
    total_height = 4.0
    wg_width = 0.5
    
    # Visual estimates based on aspect ratio
    coupler_length = 60.0
    bend_length = (total_length - coupler_length) / 2  # 30.0um per side
    coupler_gap = 0.2
    
    # Cross-section definition (standard strip waveguide)
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Create the Central Coupling Region
    # Function: coupler_straight (Two parallel straight waveguides)
    coupler = c << gf.components.coupler_straight(
        length=coupler_length,
        gap=coupler_gap,
        cross_section=xs
    )
    
    # 3. Create the S-Bends
    # Calculate geometry for the bends to fit the height constraint
    # Inner y-position (at coupler): +/- (gap/2 + width/2)
    y_inner = (coupler_gap + wg_width) / 2
    
    # Outer y-position (at ports): Target +/- 1.5 to fit within 4.0 height
    # (1.5 top + 0.25 half-width = 1.75 < 2.0 limit)
    y_outer = 1.5
    
    dy = y_outer - y_inner
    
    # Create the S-bend geometry component once
    bend_s = gf.components.bend_s(
        size=(bend_length, dy), 
        cross_section=xs
    )

    # 4. Assemble and Route (Connect bends to coupler)
    
    # --- Output Side (Right) ---
    # Top Right Arm
    bt_r = c << bend_s
    bt_r.connect("o1", coupler.ports["o3"]) # Connect to Top-East port
    
    # Bottom Right Arm (Mirrored vertically)
    bb_r = c << bend_s
    bb_r.mirror_y()
    bb_r.connect("o1", coupler.ports["o4"]) # Connect to Bottom-East port

    # --- Input Side (Left) ---
    # Top Left Arm (Mirrored horizontally)
    bt_l = c << bend_s
    bt_l.mirror_x()
    bt_l.connect("o1", coupler.ports["o1"]) # Connect to Top-West port

    # Bottom Left Arm (Mirrored horizontally and vertically)
    bb_l = c << bend_s
    bb_l.mirror_x()
    bb_l.mirror_y()
    bb_l.connect("o1", coupler.ports["o2"]) # Connect to Bottom-West port

    # 5. Expose Ports (Optional, for good practice)
    c.add_port("o1", port=bt_l.ports["o2"])
    c.add_port("o2", port=bb_l.ports["o2"])
    c.add_port("o3", port=bt_r.ports["o2"])
    c.add_port("o4", port=bb_r.ports["o2"])

    return c

# Generate and Save
device = directional_coupler_120x4()
device.show() # View in KLayout/GDS viewer
device.write_gds("directional_coupler_recreated.gds")

# Verify constraints
print(f"Device size: {device.size_info.width} x {device.size_info.height}")