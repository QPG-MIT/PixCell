import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Recreation of the directional coupler image with a 4um x 240um footprint.
    """
    c = gf.Component()
    
    # 1. Define Cross Section and Dimensions
    width = 0.5
    xs = gf.cross_section.strip(width=width)
    
    # Dimensions derived from 4um x 240um constraint
    # Y-axis calculations
    total_height = 4.0
    gap = 0.2
    
    y_outer_center = (total_height - width) / 2  # 1.75
    y_inner_center = (width + gap) / 2           # 0.35
    dy = y_outer_center - y_inner_center         # 1.4 (Vertical shift for S-bends)
    
    # X-axis calculations (Total = 240)
    l_straight = 20.0
    l_sbend = 50.0
    l_coupler = 100.0

    # 2. Create Primitives
    
    # The Central Coupling Region
    # gf.components.coupler_straight creates two parallel waveguides
    coupler = c << gf.components.coupler_straight(
        length=l_coupler, 
        gap=gap, 
        cross_section=xs
    )

    # The Input/Output Straights
    straight = gf.components.straight(length=l_straight, cross_section=xs)

    # The S-Bends (Transitions)
    # We need specific S-bends for traversing Up and Down
    # bend_s geometry: size=(length, height_change)
    
    # S-bend moving UP (Low -> High)
    bend_up = gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    # S-bend moving DOWN (High -> Low)
    bend_down = gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)

    # 3. Assembly - Left Side (Inputs)
    # We work backwards from the coupler to the inputs
    
    # Top-Left S-bend: Needs to go from High (Input) to Low (Coupler).
    # We attach the END (o2) of a "High->Low" bend to the coupler.
    sb_in_top = c << bend_down
    sb_in_top.connect("o2", coupler.ports["o1"]) 
    
    # Bottom-Left S-bend: Needs to go from Low (Input) to High (Coupler).
    # We attach the END (o2) of a "Low->High" bend to the coupler.
    sb_in_bot = c << bend_up
    sb_in_bot.connect("o2", coupler.ports["o2"])

    # Attach Input Straights
    wg_in_top = c << straight
    wg_in_top.connect("o2", sb_in_top.ports["o1"])
    
    wg_in_bot = c << straight
    wg_in_bot.connect("o2", sb_in_bot.ports["o1"])

    # 4. Assembly - Right Side (Outputs)
    # We work forwards from the coupler to the outputs
    
    # Top-Right S-bend: Needs to go from Low (Coupler) to High (Output).
    sb_out_top = c << bend_up
    sb_out_top.connect("o1", coupler.ports["o3"])
    
    # Bottom-Right S-bend: Needs to go from High (Coupler) to Low (Output).
    sb_out_down = c << bend_down
    sb_out_down.connect("o1", coupler.ports["o4"])
    
    # Attach Output Straights
    wg_out_top = c << straight
    wg_out_top.connect("o1", sb_out_top.ports["o2"])
    
    wg_out_bot = c << straight
    wg_out_bot.connect("o1", sb_out_down.ports["o2"])

    # 5. Expose Ports
    c.add_port("o1", port=wg_in_top.ports["o1"]) # Top Input
    c.add_port("o2", port=wg_in_bot.ports["o1"]) # Bottom Input
    c.add_port("o3", port=wg_out_top.ports["o2"]) # Top Output
    c.add_port("o4", port=wg_out_bot.ports["o2"]) # Bottom Output

    return c

# Create and write
if __name__ == "__main__":
    c = directional_coupler_4x240()
    c.show() # View in KLayout
    c.write_gds("directional_coupler.gds")
    
    # Verification print
    print(f"Device Size: {c.size_info.width} x {c.size_info.height}")