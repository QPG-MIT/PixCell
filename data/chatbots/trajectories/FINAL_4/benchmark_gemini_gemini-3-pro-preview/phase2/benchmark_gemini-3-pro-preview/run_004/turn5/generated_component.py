import gdsfactory as gf

@gf.cell
def directional_coupler_refined_v4():
    """
    Creates an adiabatic directional coupler matching the target geometry.
    
    Adjustments for Iteration 5:
    - Analyzed the raster output of V3 (l_straight=4.5um). The central parallel region 
      was still significantly shorter than the target image. The target shows a 
      dominant "bar-like" interaction region occupying roughly half the device length.
    - Increased `l_straight` to 9.0um (from 4.5um). This sets the coupling length to 
      50% of the total footprint, matching the visual proportions of the target much closer.
    - Correspondingly reduced `l_sbend` to 4.5um to maintain the fixed 18.0um total length.
    - Vertical parameters (3.0um height, 0.3um gap, 0.5um width) remain validated 
      and unchanged.
    """
    c = gf.Component()

    # 1. Define Geometric Parameters
    length_total = 18.0
    
    # REFINED LENGTH DISTRIBUTION (Iter 5)
    # Increasing straight section to 9.0um (50% of total length) to match the 
    # extended parallel interaction region seen in the target image.
    l_straight = 9.0  
    l_sbend = (length_total - l_straight) / 2  # (18 - 9)/2 = 4.5
    
    wg_width = 0.5
    gap_coupling = 0.3
    
    # 2. Calculate Vertical Geometry
    # Constraint: Total height = 3.0um. 
    # Waveguide width 0.5um.
    # Top edge at y = +1.5, Bottom edge at y = -1.5.
    # Top center: 1.5 - 0.25 = 1.25
    y_in_top = 1.25
    y_in_bot = -1.25
    
    # Coupling region centers
    # Gap center y = 0. Inner edges at +/- 0.15.
    # Top wg center = 0.15 + (0.5/2) = 0.4
    y_couple_top = (gap_coupling + wg_width) / 2
    y_couple_bot = -y_couple_top
    
    # Vertical displacement for the S-bends
    # Top input bends DOWN (-dy) to reach coupler
    dy = y_in_top - y_couple_top  # 1.25 - 0.4 = 0.85

    # 3. Define Cross Section
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        radius=None, 
        layer=(1, 0)
    )

    # 4. Construct Top Arm
    # Input S-bend (bends down to coupler)
    # size=(x, y): Positive x, negative y for downward bend
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
    # size=(x, y): Positive x, positive y for upward bend
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
device = directional_coupler_refined_v4()
device.write_gds("directional_coupler_refined_v4.gds")