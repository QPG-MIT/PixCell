import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreation of the directional coupler based on image analysis.
    Footprint constrained to 4 um x 240 um.
    """
    c = gf.Component()

    # 1. Define Parameters
    # --------------------
    # Geometry
    total_length = 240.0
    wg_width = 0.5
    gap = 0.2
    
    # Longitudinal (X) Dimensions
    len_straight_io = 20.0   # Input/Output lead length
    len_bend = 60.0          # S-bend length
    len_coupler = 80.0       # Interaction region length
    
    # Vertical (Y) Dimensions
    y_input_offset = 1.5     # Input waveguide center Y (+/- 1.5 gives 3.0 separation)
    y_coupler_offset = (wg_width + gap) / 2  # Coupler waveguide center Y (+/- 0.35)
    dy_bend = y_input_offset - y_coupler_offset # The vertical shift required (1.15)

    # Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Create Primitives
    # --------------------
    
    # A. Central Coupling Region
    # Creates two parallel straights with the specified gap
    coupler_core = c << gf.components.coupler_straight(
        length=len_coupler,
        gap=gap,
        cross_section=xs
    )
    
    # B. S-Bends (Transitions)
    # Note: bend_s(size=(x, y)). 
    # For Top Left: we go from high Y to low Y (negative dy)
    # For Bot Left: we go from low Y to high Y (positive dy)
    bend_s_down = gf.components.bend_s(size=(len_bend, -dy_bend), cross_section=xs)
    bend_s_up   = gf.components.bend_s(size=(len_bend, dy_bend), cross_section=xs)

    # C. Straight Leads (Input/Output handles)
    straight_io = gf.components.straight(length=len_straight_io, cross_section=xs)

    # 3. Assembly (Connecting Components)
    # -----------------------------------
    
    # --- Left Side (Inputs) ---
    
    # Top Left Bend
    bl_top = c << bend_s_down
    bl_top.connect("o2", coupler_core.ports["o1"]) # Connect end of bend to coupler input
    
    # Top Left Straight Input
    sl_top = c << straight_io
    sl_top.connect("o2", bl_top.ports["o1"])

    # Bottom Left Bend
    bl_bot = c << bend_s_up
    bl_bot.connect("o2", coupler_core.ports["o2"])
    
    # Bottom Left Straight Input
    sl_bot = c << straight_io
    sl_bot.connect("o2", bl_bot.ports["o1"])

    # --- Right Side (Outputs) ---
    
    # Top Right Bend (Goes back up from coupler to output)
    br_top = c << bend_s_up
    br_top.connect("o1", coupler_core.ports["o3"]) # Connect start of bend to coupler output
    
    # Top Right Straight Output
    sr_top = c << straight_io
    sr_top.connect("o1", br_top.ports["o2"])

    # Bottom Right Bend (Goes back down)
    br_bot = c << bend_s_down
    br_bot.connect("o1", coupler_core.ports["o4"])
    
    # Bottom Right Straight Output
    sr_bot = c << straight_io
    sr_bot.connect("o1", br_bot.ports["o2"])

    # 4. Expose Ports
    # ---------------
    c.add_port("o1", port=sl_top.ports["o1"]) # Top Input
    c.add_port("o2", port=sl_bot.ports["o1"]) # Bottom Input
    c.add_port("o3", port=sr_top.ports["o2"]) # Top Output
    c.add_port("o4", port=sr_bot.ports["o2"]) # Bottom Output

    return c

# Generate and save the device
device = directional_coupler_4x240()
device.show() # View in KLayout
device.write_gds("directional_coupler_4x240.gds")

# Print verification of footprint
print(f"Device Size: {device.size_info.width} x {device.size_info.height}")