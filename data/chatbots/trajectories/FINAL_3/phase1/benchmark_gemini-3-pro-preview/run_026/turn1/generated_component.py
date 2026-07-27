import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Directional Coupler with precise footprint constraints.
    Footprint: 4 um (y) x 240 um (x).
    """
    c = gf.Component()

    # --- 1. Dimensions & Constraints ---
    total_length = 240.0
    total_height = 4.0
    wg_width = 0.5
    gap = 0.2  # Coupling gap
    
    # Length budget
    len_straight = 20.0
    len_coupler = 40.0
    # Remaining length divided by 2 (left side and right side)
    len_bend = (total_length - len_coupler - 2 * len_straight) / 2  # (240 - 40 - 40)/2 = 80.0

    # Vertical budget
    # We calculate the Y-center position of the outer waveguides to hit exactly 4.0um edge-to-edge
    # Top edge: +2.0, Bottom edge: -2.0
    # Top center: 2.0 - (0.5/2) = 1.75
    y_center_outer = (total_height / 2) - (wg_width / 2)
    
    # Calculate Y-center of the inner waveguides (at the coupler)
    # Gap center is 0. Inner edge is gap/2. Center is gap/2 + width/2.
    y_center_inner = (gap / 2) + (wg_width / 2)
    
    # The vertical shift required for the S-bend (dy)
    dy = y_center_outer - y_center_inner  # 1.75 - 0.35 = 1.4

    # Define Cross Section
    xs = gf.cross_section.strip(width=wg_width)

    # --- 2. Create Primitives ---
    
    # Central Coupler
    # coupler_straight creates two parallel waveguides centered at y=0
    coupler = c << gf.components.coupler_straight(
        length=len_coupler, 
        gap=gap, 
        cross_section=xs
    )

    # S-Bend
    # We define a generic S-bend with the calculated dimensions
    s_bend_ref = gf.components.bend_s(
        size=(len_bend, dy), 
        cross_section=xs
    )

    # Straight section
    straight_ref = gf.components.straight(
        length=len_straight, 
        cross_section=xs
    )

    # --- 3. Assembly (Connecting Ports) ---

    # -- LEFT SIDE (Inputs) --
    
    # Top Left (Input 1)
    # We mirror the S-bend vertically to transition "down" from the outer edge to the coupler
    bl_top = c << s_bend_ref
    bl_top.mirror_y()
    # Connect the END (o2) of the bend to the coupler input (o1)
    bl_top.connect("o2", coupler.ports["o1"])
    
    # Attach straight input to the start of the bend
    sl_top = c << straight_ref
    sl_top.connect("o2", bl_top.ports["o1"])

    # Bottom Left (Input 2)
    # Standard S-bend transitions "up" from the outer edge to the coupler
    bl_bot = c << s_bend_ref
    bl_bot.connect("o2", coupler.ports["o2"])
    
    # Attach straight input
    sl_bot = c << straight_ref
    sl_bot.connect("o2", bl_bot.ports["o1"])

    # -- RIGHT SIDE (Outputs) --

    # Top Right (Output 1)
    # Standard S-bend transitions "up" from the coupler to the outer edge
    br_top = c << s_bend_ref
    br_top.connect("o1", coupler.ports["o4"])
    
    # Attach straight output
    sr_top = c << straight_ref
    sr_top.connect("o1", br_top.ports["o2"])

    # Bottom Right (Output 2)
    # Mirror S-bend transitions "down" from the coupler to the outer edge
    br_bot = c << s_bend_ref
    br_bot.mirror_y()
    br_bot.connect("o1", coupler.ports["o3"])
    
    # Attach straight output
    sr_bot = c << straight_ref
    sr_bot.connect("o1", br_bot.ports["o2"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=sl_bot.ports["o1"])
    c.add_port("o2", port=sl_top.ports["o1"])
    c.add_port("o3", port=sr_top.ports["o2"])
    c.add_port("o4", port=sr_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # 1. Create the device
    device = directional_coupler_4x240()
    
    # 2. Validate dimensions
    print(f"Device Size: {device.size_info.width:.2f} x {device.size_info.height:.2f} um")
    
    # 3. Save to GDS file
    gds_filename = "directional_coupler_4x240.gds"
    device.write_gds(gds_filename)
    print(f"Geometry saved to {gds_filename}")
    
    # 4. Optional: View
    try:
        device.show()
    except Exception:
        pass