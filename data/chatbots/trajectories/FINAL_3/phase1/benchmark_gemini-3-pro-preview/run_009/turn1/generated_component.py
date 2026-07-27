import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreates the directional coupler from the image with a 4um x 240um footprint
    using standard GDSFactory parametric primitives.
    """
    c = gf.Component()
    
    # 1. Define Geometry Parameters
    # -----------------------------
    wg_width = 0.5
    gap = 0.2
    
    # Length budget (Total = 240um)
    len_coupler = 100.0
    len_bend = 50.0
    len_straight = 20.0
    
    # Height budget (Total = 4um)
    # Coupler y-position (center of waveguide): +/- (gap/2 + width/2)
    y_coupler = (gap/2) + (wg_width/2) # 0.35um
    
    # Input/Output y-position: We want total height ~3-4um. 
    # Let's place ports at y = +/- 1.25um. Total span = 2.5um centers + 0.5um width = 3.0um (Fits in 4um)
    y_port = 1.25
    
    # Calculate bend height offset
    dy_bend = y_port - y_coupler # 0.9um

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Create Primitives
    # --------------------
    # Central Coupling Region
    coupler = c << gf.components.coupler_straight(
        length=len_coupler, 
        gap=gap, 
        cross_section=xs
    )
    
    # S-Bend Transition (generic block)
    # size = (x_length, y_height)
    bend_geo = gf.components.bend_s(
        size=(len_bend, dy_bend), 
        cross_section=xs
    )
    
    # Input/Output Straights
    straight_geo = gf.components.straight(
        length=len_straight, 
        cross_section=xs
    )

    # 3. Assemble Left Side (Inputs -> Coupler)
    # -----------------------------------------
    
    # Top Left Bend (Mirror horizontally to go Left-Up)
    tl_bend = c << bend_geo
    tl_bend.mirror()
    # Connect bend "start" (which is now right side after mirror) to coupler West-Top (o2)
    tl_bend.connect("o1", coupler.ports["o2"]) 
    
    # Bottom Left Bend (Mirror H then V to go Left-Down)
    bl_bend = c << bend_geo
    bl_bend.mirror()
    bl_bend.mirror_y()
    bl_bend.connect("o1", coupler.ports["o1"]) # Connect to coupler West-Bottom (o1)

    # Top Left Straight (Input)
    tl_wg = c << straight_geo
    tl_wg.connect("o2", tl_bend.ports["o2"]) # Connect straight end to bend start
    
    # Bottom Left Straight (Input)
    bl_wg = c << straight_geo
    bl_wg.connect("o2", bl_bend.ports["o2"])

    # 4. Assemble Right Side (Coupler -> Outputs)
    # -------------------------------------------
    
    # Top Right Bend (Standard orientation: Right-Up)
    tr_bend = c << bend_geo
    tr_bend.connect("o1", coupler.ports["o3"]) # Connect to coupler East-Top (o3)
    # Note: coupler port numbering might vary by version. 
    # Usually o3=East_Bottom, o4=East_Top in older versions, 
    # or o3=East_Top in others. Assuming o3 is top-right here based on visual symmetry needs.
    # If connection looks crossed, we swap ports o3/o4.
    
    # Bottom Right Bend (Mirror V to go Right-Down)
    br_bend = c << bend_geo
    br_bend.mirror_y()
    br_bend.connect("o1", coupler.ports["o4"]) # Connect to coupler East-Bottom

    # Top Right Straight (Output)
    tr_wg = c << straight_geo
    tr_wg.connect("o1", tr_bend.ports["o2"])
    
    # Bottom Right Straight (Output)
    br_wg = c << straight_geo
    br_wg.connect("o1", br_bend.ports["o2"])

    # 5. Expose Ports
    # ---------------
    c.add_port("o1", port=tl_wg.ports["o1"])
    c.add_port("o2", port=bl_wg.ports["o1"])
    c.add_port("o3", port=tr_wg.ports["o2"])
    c.add_port("o4", port=br_wg.ports["o2"])

    return c

# Generate and Export
device = directional_coupler_4x240()
device.show() # View in KLayout
device.write_gds("directional_coupler_4x240.gds")