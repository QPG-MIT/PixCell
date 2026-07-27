import gdsfactory as gf

@gf.cell
def directional_coupler_240():
    """
    Creates a directional coupler based on visual analysis and footprint constraints.
    Footprint: 4 um (height) x 240 um (length)
    """
    c = gf.Component()
    
    # 1. Define Cross Section
    # Assuming standard silicon waveguide width
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # 2. Define Dimensions based on Footprint (4um x 240um)
    L_total = 240.0
    H_total = 4.0
    
    wg_width = 0.5
    gap = 0.2
    
    # Longitudinal partitions (Estimated from image proportions)
    l_couple = 100.0
    l_bend = 50.0
    l_io = (L_total - l_couple - 2*l_bend) / 2  # Result: 20.0
    
    # Vertical calculations
    # y_center_io is the Y-coordinate of the input/output arms
    y_center_io = (H_total - wg_width) / 2  # (4 - 0.5)/2 = 1.75
    
    # y_center_couple is the Y-coordinate of the central coupling arms
    y_center_couple = (gap + wg_width) / 2  # (0.2 + 0.5)/2 = 0.35
    
    # dy is the vertical shift required for the S-bend
    dy = y_center_io - y_center_couple      # 1.75 - 0.35 = 1.4

    # 3. Create Primitives
    # Straight for the central coupling region
    wg_couple = gf.components.straight(length=l_couple, cross_section=xs)
    
    # Straight for the input/output ports
    wg_io = gf.components.straight(length=l_io, cross_section=xs)
    
    # S-Bend for the transition (size = length, height_shift)
    # This creates a bend that goes Right and Up by default
    bend_s = gf.components.bend_s(size=(l_bend, dy), cross_section=xs)

    # 4. Assembly - Top Arm
    # Center
    top_c = c << wg_couple
    top_c.x = 0
    top_c.y = y_center_couple
    
    # Right Side (Output)
    # Connect S-bend to right of coupler (Goes Right and Up)
    top_br = c << bend_s
    top_br.connect("o1", top_c.ports["o2"])
    
    # Connect Straight to S-bend
    top_out = c << wg_io
    top_out.connect("o1", top_br.ports["o2"])
    
    # Left Side (Input)
    # We need a bend that goes Left and Up. We mirror the standard bend horizontally.
    top_bl = c << bend_s
    top_bl.mirror() 
    top_bl.connect("o1", top_c.ports["o1"])
    
    # Connect Straight to S-bend
    top_in = c << wg_io
    top_in.connect("o2", top_bl.ports["o2"])

    # 5. Assembly - Bottom Arm
    # The bottom arm is symmetric to the top.
    # Center
    bot_c = c << wg_couple
    bot_c.x = 0
    bot_c.y = -y_center_couple
    
    # Right Side (Output)
    # Need bend that goes Right and Down. Mirror standard bend vertically.
    bot_br = c << bend_s
    bot_br.mirror_y()
    bot_br.connect("o1", bot_c.ports["o2"])
    
    bot_out = c << wg_io
    bot_out.connect("o1", bot_br.ports["o2"])
    
    # Left Side (Input)
    # Need bend that goes Left and Down. Mirror standard bend X and Y.
    bot_bl = c << bend_s
    bot_bl.mirror() # Flip X
    bot_bl.mirror_y() # Flip Y
    bot_bl.connect("o1", bot_c.ports["o1"])
    
    bot_in = c << wg_io
    bot_in.connect("o2", bot_bl.ports["o2"])

    # 6. Expose Ports
    c.add_port("o1", port=top_in.ports["o1"]) # Top Input
    c.add_port("o2", port=bot_in.ports["o1"]) # Bottom Input
    c.add_port("o3", port=top_out.ports["o2"]) # Top Output
    c.add_port("o4", port=bot_out.ports["o2"]) # Bottom Output

    return c

if __name__ == "__main__":
    # Generate and show
    component = directional_coupler_240()
    component.show()
    
    # Optional: Verify footprint
    print(f"Device Size: {component.size_info}")
    # Write to GDS
    component.write_gds("directional_coupler.gds")