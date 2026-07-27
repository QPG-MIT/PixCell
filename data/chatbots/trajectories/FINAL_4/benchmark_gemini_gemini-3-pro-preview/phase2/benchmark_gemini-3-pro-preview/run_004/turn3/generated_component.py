import gdsfactory as gf

@gf.cell
def directional_coupler_refined_v2():
    """
    Creates an adiabatic directional coupler matching the target geometry.
    
    Adjustments based on visual feedback:
    - Reduced straight coupling length (l_straight) significantly (8.0 -> 2.0). 
      The previous iteration had a very long parallel section ("dumbbell" shape), 
      while the target image shows a smooth, continuous transition with a minimal 
      but distinct "waist".
    - Increased S-bend length (l_sbend) (5.0 -> 8.0). This stretches the transition 
      region, creating the gentle, sweeping curves seen in the target.
    - Preserved vertical parameters (Height=3.0um, Gap=0.3um) which match the 
      footprint and visual proportions well.
    """
    c = gf.Component()

    # 1. Define Geometric Parameters
    length_total = 18.0
    
    # REFINED LENGTH DISTRIBUTION
    # Target image shows the bends dominating the geometry with a short central waist.
    l_straight = 2.0  
    l_sbend = (length_total - l_straight) / 2  # (18 - 2)/2 = 8.0
    
    wg_width = 0.5
    gap_coupling = 0.3
    
    # 2. Calculate Vertical Geometry
    # Constraint: Total height = 3.0um.
    # Waveguides are centered at +/- 1.25um to fit within +/- 1.5um bounds with 0.5um width.
    y_in_top = 1.25
    y_in_bot = -1.25
    
    # Coupling region centers
    # Inner edge at gap/2 = 0.15. Center = 0.15 + width/2 = 0.4
    y_couple_top = (gap_coupling + wg_width) / 2
    y_couple_bot = -y_couple_top
    
    # Vertical displacement for the S-bend
    dy = y_in_top - y_couple_top  # 1.25 - 0.4 = 0.85

    # 3. Define Cross Section
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        radius=None, 
        layer=(1, 0)
    )

    # 4. Construct Top Arm
    # Input S-bend (bends down to coupler)
    bend_top_in = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    bend_top_in.move((0, y_in_top))
    
    # Central Straight
    straight_top = c << gf.components.straight(length=l_straight, cross_section=xs)
    straight_top.connect("o1", bend_top_in.ports["o2"])
    
    # Output S-bend (bends up to output)
    bend_top_out = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    bend_top_out.connect("o1", straight_top.ports["o2"])

    # 5. Construct Bottom Arm
    # Input S-bend (bends up to coupler)
    bend_bot_in = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    bend_bot_in.move((0, y_in_bot))
    
    # Central Straight
    straight_bot = c << gf.components.straight(length=l_straight, cross_section=xs)
    straight_bot.connect("o1", bend_bot_in.ports["o2"])
    
    # Output S-bend (bends down to output)
    bend_bot_out = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    bend_bot_out.connect("o1", straight_bot.ports["o2"])

    # 6. Expose Ports
    c.add_port("o1", port=bend_top_in.ports["o1"])
    c.add_port("o2", port=bend_bot_in.ports["o1"])
    c.add_port("o3", port=bend_top_out.ports["o2"])
    c.add_port("o4", port=bend_bot_out.ports["o2"])

    return c

# Create and save
device = directional_coupler_refined_v2()
device.write_gds("directional_coupler_refined_v2.gds")