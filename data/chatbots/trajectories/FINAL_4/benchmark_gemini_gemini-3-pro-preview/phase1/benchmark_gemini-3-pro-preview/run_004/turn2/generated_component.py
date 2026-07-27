import gdsfactory as gf

@gf.cell
def directional_coupler_refined():
    """
    Creates an adiabatic directional coupler.
    Refined parameters:
    - Increased coupling gap to 0.3um to match visual proportions.
    - Adjusted lengths (Short S-bends, Long Straight) to match the steepness 
      of the transition and the dominant coupling length in the image.
    """
    c = gf.Component()

    # 1. Define Geometric Parameters
    length_total = 18.0
    
    # Adjusted lengths based on visual analysis:
    # shorter transitions (5um) and a longer central region (8um).
    l_sbend = 5.0
    l_straight = 8.0 
    
    wg_width = 0.5
    gap_coupling = 0.3  # Increased from 0.2 to match visual spacing
    
    # 2. Calculate Vertical Geometry
    # Device footprint height: 3.0um (-1.5 to 1.5)
    # Input centers: 1.5 (edge) - 0.25 (half width) = 1.25
    y_in_top = 1.25
    y_in_bot = -1.25
    
    # Coupling centers: 
    # Center = (gap / 2) + (wg_width / 2)
    y_couple_top = (gap_coupling + wg_width) / 2  # (0.3 + 0.5)/2 = 0.4
    y_couple_bot = -y_couple_top
    
    # Calculate vertical shift for S-bends
    dy = y_in_top - y_couple_top  # 1.25 - 0.4 = 0.85

    # 3. Define Cross Section
    # Relax radius_min to allow for the steeper 5um long S-bends
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        radius=4.0,     # Reduced nominal radius
        radius_min=3.0, # Allow tighter bends for the compact transition
        layer=(1, 0)
    )

    # 4. Construct Top Arm
    # Input S-bend (Down)
    bend_top_in = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    bend_top_in.move((0, y_in_top))
    
    # Central Straight
    straight_top = c << gf.components.straight(length=l_straight, cross_section=xs)
    straight_top.connect("o1", bend_top_in.ports["o2"])
    
    # Output S-bend (Up)
    bend_top_out = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    bend_top_out.connect("o1", straight_top.ports["o2"])

    # 5. Construct Bottom Arm
    # Input S-bend (Up)
    bend_bot_in = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    bend_bot_in.move((0, y_in_bot))
    
    # Central Straight
    straight_bot = c << gf.components.straight(length=l_straight, cross_section=xs)
    straight_bot.connect("o1", bend_bot_in.ports["o2"])
    
    # Output S-bend (Down)
    bend_bot_out = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    bend_bot_out.connect("o1", straight_bot.ports["o2"])

    # 6. Expose Ports
    c.add_port("o1", port=bend_top_in.ports["o1"])
    c.add_port("o2", port=bend_bot_in.ports["o1"])
    c.add_port("o3", port=bend_top_out.ports["o2"])
    c.add_port("o4", port=bend_bot_out.ports["o2"])

    return c

# Create and save
device = directional_coupler_refined()
device.write_gds("directional_coupler_refined.gds")