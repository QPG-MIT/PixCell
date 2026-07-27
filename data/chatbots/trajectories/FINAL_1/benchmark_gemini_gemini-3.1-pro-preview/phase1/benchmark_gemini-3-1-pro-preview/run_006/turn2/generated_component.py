import gdsfactory as gf

@gf.cell
def adiabatic_coupler() -> gf.Component:
    """
    Parametric creation of an adiabatic mode sorter / directional coupler.
    Total Footprint: 40.0um x 1.7um.
    """
    c = gf.Component("adiabatic_coupler")
    LAYER = (1, 0)
    
    # ---------------------------------------------------------
    # Geometry Definitions & Lengths
    # Total Length = 25.0 + 10.0 + 5.0 = 40.0 um
    # Total Height (set by outer straight sections) = 1.7 um
    # ---------------------------------------------------------
    L_taper = 25.0
    L_sbend = 10.0
    L_straight = 5.0
    
    # Center Arm Cross Sections
    # Tapers from a wide 0.45um down to a sharp 0.05um tip
    xs_c_in = gf.cross_section.cross_section(width=0.45, offset=0.0, layer=LAYER)
    xs_c_out = gf.cross_section.cross_section(width=0.05, offset=0.0, layer=LAYER)
    
    # Top Arm Cross Sections
    # At input: Center is pushed out to +0.40 um offset to leave a wide gap
    # At mid: Center pinches inwards to +0.30 um offset, narrowing the gap
    xs_t_in = gf.cross_section.cross_section(width=0.15, offset=0.40, layer=LAYER)
    xs_t_mid = gf.cross_section.cross_section(width=0.50, offset=0.30, layer=LAYER)
    
    # Bottom Arm Cross Sections (Symmetric to Top)
    xs_b_in = gf.cross_section.cross_section(width=0.15, offset=-0.40, layer=LAYER)
    xs_b_mid = gf.cross_section.cross_section(width=0.50, offset=-0.30, layer=LAYER)

    # ---------------------------------------------------------
    # 1. Center Arm
    # ---------------------------------------------------------
    trans_c = gf.path.transition(xs_c_in, xs_c_out, width_type='linear')
    center_taper = c << gf.path.extrude_transition(gf.path.straight(length=L_taper), trans_c)

    # ---------------------------------------------------------
    # 2. Top Outer Arm
    # ---------------------------------------------------------
    # The taper transitions both width (0.15 -> 0.50) and offset (0.40 -> 0.30)
    trans_t = gf.path.transition(xs_t_in, xs_t_mid, width_type='linear')
    top_taper = c << gf.path.extrude_transition(gf.path.straight(length=L_taper), trans_t)
    
    # S-bend shifts the underlying PATH by +0.30. 
    # Since xs_t_mid retains a +0.30 offset, the final routing centers perfectly at +0.60
    top_sbend = c << gf.components.bend_s(size=(L_sbend, 0.30), cross_section=xs_t_mid)
    top_sbend.connect("o1", top_taper.ports["o2"])
    
    # Final top straight routing (Centered at Y = +0.60. Max Y edge = +0.85)
    top_straight = c << gf.components.straight(length=L_straight, cross_section=xs_t_mid)
    top_straight.connect("o1", top_sbend.ports["o2"])

    # ---------------------------------------------------------
    # 3. Bottom Outer Arm
    # ---------------------------------------------------------
    # Symmetrical taper transitioning width and offset
    trans_b = gf.path.transition(xs_b_in, xs_b_mid, width_type='linear')
    bot_taper = c << gf.path.extrude_transition(gf.path.straight(length=L_taper), trans_b)
    
    # S-bend shifts path by -0.30. Together with offset -0.30, final routing centers at -0.60
    bot_sbend = c << gf.components.bend_s(size=(L_sbend, -0.30), cross_section=xs_b_mid)
    bot_sbend.connect("o1", bot_taper.ports["o2"])
    
    # Final bot straight routing (Centered at Y = -0.60. Min Y edge = -0.85)
    bot_straight = c << gf.components.straight(length=L_straight, cross_section=xs_b_mid)
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
    device = adiabatic_coupler()
    # Save the GDS file explicitly 
    device.write_gds("adiabatic_coupler.gds")