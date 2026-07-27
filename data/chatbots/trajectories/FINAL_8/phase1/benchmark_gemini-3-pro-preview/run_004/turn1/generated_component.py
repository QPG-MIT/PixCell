import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreation of the directional coupler device based on the image 
    and provided parametric catalog.
    
    Footprint target: 120um x 4um
    """
    c = gf.Component()

    # 1. Define Parameters based on visual analysis and constraints
    total_length = 120.0
    total_height = 4.0
    
    # Geometry splits
    straight_length = 80.0
    sbend_length = (total_length - straight_length) / 2  # 20.0 um
    
    # Y-positions
    # The device spans 4um total, so ports are at y = +2.0 and -2.0
    port_y_offset = total_height / 2
    
    # The coupling region looks compact. Let's assume the main guides 
    # sit closer to the center in the straight region.
    coupling_y_offset = 0.7 
    
    # Calculate the S-bend vertical shift (dy)
    # Shift = Final Y - Initial Y (or vice versa)
    bend_dy = port_y_offset - coupling_y_offset

    # 2. Define Cross Sections (using generic layer 1,0)
    # "Thick" black lines for main guides
    xs_main = gf.cross_section.cross_section(width=0.8, layer=(1, 0))
    # "Thin" black lines for the internal stripes
    xs_thin = gf.cross_section.cross_section(width=0.15, layer=(1, 0))

    # ==========================================
    # 3. Construct Central Coupling Region
    # ==========================================
    
    # A. Main Top Bus (Straight)
    main_top = c << gf.components.straight(length=straight_length, cross_section=xs_main)
    main_top.y = coupling_y_offset
    
    # B. Main Bottom Bus (Straight)
    main_bot = c << gf.components.straight(length=straight_length, cross_section=xs_main)
    main_bot.y = -coupling_y_offset
    
    # C. Inner Stripes (The distinct lines in the middle gap)
    # Visually, there are about 3 thin lines between the main guides
    for y_pos in [0, 0.3, -0.3]:
        stripe = c << gf.components.straight(length=straight_length, cross_section=xs_thin)
        stripe.y = y_pos

    # ==========================================
    # 4. Construct Input/Output S-Bends
    # ==========================================
    
    # Define the S-bend geometry using the calculated size
    # size = (length, height_drop)
    bend_geo = gf.components.bend_s(
        size=(sbend_length, bend_dy), 
        cross_section=xs_main
    )

    # --- Left Side (Inputs) ---
    
    # Top Left Input
    # We mirror it horizontally so it connects from left-to-right into the straight
    tl_bend = c << bend_geo
    tl_bend.mirror() 
    tl_bend.connect("o1", main_top.ports["o1"])
    
    # Bottom Left Input
    # Needs to mirror vertically to go "up" into the straight, and horizontally for input
    bl_bend = c << bend_geo
    bl_bend.mirror() # Horizontal mirror
    bl_bend.mirror_y() # Vertical flip
    bl_bend.connect("o1", main_bot.ports["o1"])

    # --- Right Side (Outputs) ---
    
    # Top Right Output
    # Standard orientation works for going "out" and "up"
    tr_bend = c << bend_geo
    tr_bend.connect("o1", main_top.ports["o2"])
    
    # Bottom Right Output
    # Mirror Y to go "out" and "down"
    br_bend = c << bend_geo
    br_bend.mirror_y()
    br_bend.connect("o1", main_bot.ports["o2"])

    # ==========================================
    # 5. Expose Ports
    # ==========================================
    c.add_port("o1", port=tl_bend.ports["o2"])
    c.add_port("o2", port=bl_bend.ports["o2"])
    c.add_port("o3", port=tr_bend.ports["o2"])
    c.add_port("o4", port=br_bend.ports["o2"])

    return c

# Generate and save
if __name__ == "__main__":
    device = recreated_device()
    device.show() # View in KLayout
    device.write_gds("recreated_device.gds")