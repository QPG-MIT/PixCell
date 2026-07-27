import gdsfactory as gf

@gf.cell
def adiabatic_coupler() -> gf.Component:
    """
    Parametric creation of an adiabatic mode sorter / directional coupler.
    Total Footprint: 40.0um x 1.7um.
    """
    c = gf.Component("adiabatic_coupler")

    # Standard layer and cross-section for constant width routing
    LAYER = (1, 0)
    xs_std = gf.cross_section.cross_section(width=0.5, layer=LAYER)

    # ---------------------------------------------------------
    # 1. Central Arm
    # ---------------------------------------------------------
    # Tapers down from standard width to a narrow tip over 25um
    center_taper = c << gf.components.taper(
        length=25.0, 
        width1=0.5, 
        width2=0.1, 
        layer=LAYER
    )

    # ---------------------------------------------------------
    # 2. Top Outer Arm
    # ---------------------------------------------------------
    # Parallel taper expanding from thin to standard width
    top_taper = c << gf.components.taper(
        length=25.0, 
        width1=0.15, 
        width2=0.5, 
        layer=LAYER
    )
    # Move the center of the top arm up to create a constant 
    # gap between its inner edge and the central taper's outer edge.
    top_taper.move((0, 0.40))

    # S-bend moving the outer arm upwards
    top_sbend = c << gf.components.bend_s(
        size=(10.0, 0.20), 
        cross_section=xs_std
    )
    top_sbend.connect("o1", top_taper.ports["o2"])

    # Final straight routing
    top_straight = c << gf.components.straight(
        length=5.0, 
        cross_section=xs_std
    )
    top_straight.connect("o1", top_sbend.ports["o2"])

    # ---------------------------------------------------------
    # 3. Bottom Outer Arm
    # ---------------------------------------------------------
    # Symmetrical construction mirroring the top arm
    bot_taper = c << gf.components.taper(
        length=25.0, 
        width1=0.15, 
        width2=0.5, 
        layer=LAYER
    )
    bot_taper.move((0, -0.40))

    # S-bend moving the outer arm downwards (negative dy)
    bot_sbend = c << gf.components.bend_s(
        size=(10.0, -0.20), 
        cross_section=xs_std
    )
    bot_sbend.connect("o1", bot_taper.ports["o2"])

    # Final straight routing
    bot_straight = c << gf.components.straight(
        length=5.0, 
        cross_section=xs_std
    )
    bot_straight.connect("o1", bot_sbend.ports["o2"])

    # ---------------------------------------------------------
    # 4. Port Exposure
    # ---------------------------------------------------------
    c.add_port("in_center", port=center_taper.ports["o1"])
    c.add_port("in_top", port=top_taper.ports["o1"])
    c.add_port("in_bot", port=bot_taper.ports["o1"])
    c.add_port("out_top", port=top_straight.ports["o2"])
    c.add_port("out_bot", port=bot_straight.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    device = adiabatic_coupler()
    
    # Save the GDS file explicitly 
    device.write_gds("adiabatic_coupler.gds")