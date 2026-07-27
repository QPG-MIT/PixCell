import gdsfactory as gf

@gf.cell
def directional_coupler_refined_v3():
    """
    Directional coupler with adjusted proportions to closely match the target image.
    
    Refinements V3:
    - Added straight 'lead' sections at input/output (15um) to match the visual layout.
    - Shortened the S-bend length (from 35um to 15um) to create a steeper, more defined transition.
    - Increased central coupling length (50um -> 60um) to occupy approx 50% of the device length.
    - Increased waveguide width (0.6um -> 0.8um) to match the visual line weight.
    
    Partitioning (Total 120um):
    15um (Lead) - 15um (Bend) - 60um (Coupler) - 15um (Bend) - 15um (Lead)
    
    Vertical Budget (Total 4um):
    Outer edges align to the 4um footprint boundary.
    """
    c = gf.Component()

    # --- Parameters ---
    # Total constraints
    length_total = 120.0
    height_total = 4.0
    
    # Longitudinal partitioning
    length_coupler = 60.0
    length_bend = 15.0
    length_lead = (length_total - length_coupler - 2 * length_bend) / 2  # (120 - 60 - 30)/2 = 15.0
    
    # Cross-section specs
    wg_width = 0.8
    gap = 0.2
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Calculate Y-coordinates to fill the 4um footprint exactly
    # Outer ports: The edges of the waveguide touch the footprint boundary (y=+/-2.0)
    # y_center = (Height - Width) / 2
    y_top_outer = (height_total - wg_width) / 2   # (4.0 - 0.8)/2 = 1.6
    y_bot_outer = -(height_total - wg_width) / 2  # -1.6
    
    # Inner ports: Centered around y=0 with defined gap
    y_top_inner = (gap + wg_width) / 2            # (0.2 + 0.8)/2 = 0.5
    y_bot_inner = -(gap + wg_width) / 2           # -0.5
    
    # Vertical shift for S-bends
    dy = y_top_outer - y_top_inner # 1.6 - 0.5 = 1.1

    # --- Geometry Construction ---

    # 1. Leads (Input Side - Left)
    # Top Left Lead
    lead_in_top = c << gf.components.straight(length=length_lead, cross_section=xs)
    lead_in_top.move((0, y_top_outer))
    
    # Bottom Left Lead
    lead_in_bot = c << gf.components.straight(length=length_lead, cross_section=xs)
    lead_in_bot.move((0, y_bot_outer))

    # 2. Input S-Bends (Transition In)
    # Top: Drops down (dy is negative relative to start)
    bend_in_top = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_in_top.connect("o1", lead_in_top.ports["o2"])
    
    # Bottom: Rises up
    bend_in_bot = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_in_bot.connect("o1", lead_in_bot.ports["o2"])

    # 3. Central Straight Coupling Region
    # Top Coupler Arm
    wg_top = c << gf.components.straight(length=length_coupler, cross_section=xs)
    wg_top.connect("o1", bend_in_top.ports["o2"])
    
    # Bottom Coupler Arm
    wg_bot = c << gf.components.straight(length=length_coupler, cross_section=xs)
    wg_bot.connect("o1", bend_in_bot.ports["o2"])

    # 4. Output S-Bends (Transition Out)
    # Top: Rises up
    bend_out_top = c << gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_out_top.connect("o1", wg_top.ports["o2"])
    
    # Bottom: Drops down
    bend_out_bot = c << gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_bot.ports["o2"])

    # 5. Leads (Output Side - Right)
    # Top Right Lead
    lead_out_top = c << gf.components.straight(length=length_lead, cross_section=xs)
    lead_out_top.connect("o1", bend_out_top.ports["o2"])
    
    # Bottom Right Lead
    lead_out_bot = c << gf.components.straight(length=length_lead, cross_section=xs)
    lead_out_bot.connect("o1", bend_out_bot.ports["o2"])

    # --- Port Assignments ---
    c.add_port("o1", port=lead_in_bot.ports["o1"])
    c.add_port("o2", port=lead_in_top.ports["o1"])
    c.add_port("o3", port=lead_out_top.ports["o2"])
    c.add_port("o4", port=lead_out_bot.ports["o2"])

    return c

# Create and save
device = directional_coupler_refined_v3()
device.write_gds("directional_coupler_refined_v3.gds")