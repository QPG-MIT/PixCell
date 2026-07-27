import gdsfactory as gf

@gf.cell
def directional_coupler_120x4():
    """
    Creates a directional coupler matching the footprint [120, 4] um.
    Built using parametric primitives: coupler_straight and bend_s.
    """
    c = gf.Component()

    # --- Dimensions ---
    length_total = 120.0
    height_total = 4.0
    
    # Waveguide parameters
    wg_width = 0.5
    gap = 0.2
    
    # Longitudinal partitioning
    # We allocate 60um for the interaction length, leaving 30um for bends on each side.
    length_coupler = 60.0
    length_bend = (length_total - length_coupler) / 2
    
    # Vertical partitioning (Y-axis)
    # The footprint height is 4.0um. Ports are centered relative to this bounds.
    # Center y of outer ports: +/- (Height - Width)/2
    y_port_center = (height_total - wg_width) / 2  # 1.75 um
    
    # Center y of coupling waveguides: +/- (Gap + Width)/2
    y_couple_center = (gap + wg_width) / 2         # 0.35 um
    
    # The vertical offset (dy) required for the S-bends
    dy = y_port_center - y_couple_center           # 1.4 um

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width)

    # --- 1. Central Coupling Region ---
    # Creates two straight parallel waveguides
    # Ports convention: o1(bot-W), o2(top-W), o3(top-E), o4(bot-E)
    coupler_core = c << gf.components.coupler_straight(
        length=length_coupler,
        gap=gap,
        cross_section=xs
    )

    # --- 2. Input/Output Arms (S-Bends) ---
    # Define the S-bend primitive
    # bend_s geometry usually goes from (0,0) to (length, height)
    bend_ref = gf.components.bend_s(
        size=(length_bend, dy),
        cross_section=xs
    )

    # Instantiate the four arms
    in_top = c << bend_ref
    in_bot = c << bend_ref
    out_top = c << bend_ref
    out_bot = c << bend_ref

    # --- 3. Connections ---
    
    # Input Top (Top-Left)
    # Needs to transition from High Y (port) to Low Y (coupler).
    # Mirroring Y transforms the 'Up' bend to a 'Down' bend.
    in_top.mirror_y()
    in_top.connect("o2", coupler_core.ports["o2"])

    # Input Bottom (Bot-Left)
    # Transitions from Low Y (port) to High Y (coupler, relative to port).
    # Standard bend_s goes Up.
    in_bot.connect("o2", coupler_core.ports["o1"])

    # Output Top (Top-Right)
    # Transitions from Low Y (coupler) to High Y (port).
    # Standard bend_s goes Up.
    out_top.connect("o1", coupler_core.ports["o3"])

    # Output Bottom (Bot-Right)
    # Transitions from High Y (coupler) to Low Y (port).
    # Mirroring Y transforms the 'Up' bend to a 'Down' bend.
    out_bot.mirror_y()
    out_bot.connect("o1", coupler_core.ports["o4"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=in_bot.ports["o1"])
    c.add_port("o2", port=in_top.ports["o1"])
    c.add_port("o3", port=out_top.ports["o2"])
    c.add_port("o4", port=out_bot.ports["o2"])

    return c

if __name__ == "__main__":
    # Generate and save the device
    device = directional_coupler_120x4()
    device.show()
    device.write_gds("directional_coupler_120x4.gds")