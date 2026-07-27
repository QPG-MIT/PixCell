import gdsfactory as gf

@gf.cell
def trident_mode_converter():
    """
    Generates a trident-shaped mode converter matched to visual references.
    
    Design features:
    - Long straight input section (15um) to match visual aspect ratio.
    - Central taper reduces to a sharp point exactly at the merge location of the outer arms.
    - Outer arms merge seamlessly into a 1.0um wide output waveguide.
    - Complies with 40um x 1.7um footprint constraint.
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    # Longitudinal Dimensions
    length_total = 40.0
    length_straight_in = 15.0   # Significantly increased to match target image proportion
    length_straight_out = 5.0
    length_bend = length_total - length_straight_in - length_straight_out # 20.0
    
    # Transverse Dimensions
    # Height Constraint: 1.7um total
    width_outer = 0.5
    width_inner = 0.2  # Thinner inner core for clearer gap definition
    
    # Vertical Positions (Input)
    # Total height 1.7 -> Extents +/- 0.85
    # Outer WG Center = 0.85 - (0.5 / 2) = 0.6
    y_outer_in = 0.6
    
    # Vertical Positions (Output)
    # The two 0.5um outer arms merge to form a 1.0um block.
    # To touch exactly at y=0, centers must be at +/- 0.25.
    y_outer_out = 0.25
    
    layer_wg = (1, 0)
    xs_outer = gf.cross_section.cross_section(width=width_outer, layer=layer_wg)
    xs_inner = gf.cross_section.cross_section(width=width_inner, layer=layer_wg)

    # --- 1. Center Arm ---
    # Straight Input Section
    center_in = c << gf.components.straight(
        length=length_straight_in, 
        cross_section=xs_inner
    )
    center_in.movey(0)
    
    # Taper Section
    # Ends exactly where the outer arms merge for a sharp 'V' gap closure
    center_taper = c << gf.components.taper(
        length=length_bend,
        width1=width_inner,
        width2=0.0,
        layer=layer_wg
    )
    center_taper.connect("o1", center_in.ports["o2"])

    # --- 2. Top Arm ---
    # Straight Input
    top_in = c << gf.components.straight(
        length=length_straight_in, 
        cross_section=xs_outer
    )
    top_in.movey(y_outer_in)
    
    # S-Bend Transition
    # Smooth adiabatic bend moving the arm inward
    dy_top = y_outer_out - y_outer_in
    top_bend = c << gf.components.bend_s(
        size=(length_bend, dy_top), 
        cross_section=xs_outer
    )
    top_bend.connect("o1", top_in.ports["o2"])
    
    # Merged Output Section (Top half)
    top_out = c << gf.components.straight(
        length=length_straight_out, 
        cross_section=xs_outer
    )
    top_out.connect("o1", top_bend.ports["o2"])

    # --- 3. Bottom Arm ---
    # Straight Input
    bot_in = c << gf.components.straight(
        length=length_straight_in, 
        cross_section=xs_outer
    )
    bot_in.movey(-y_outer_in)
    
    # S-Bend Transition
    dy_bot = -y_outer_out - (-y_outer_in)
    bot_bend = c << gf.components.bend_s(
        size=(length_bend, dy_bot), 
        cross_section=xs_outer
    )
    bot_bend.connect("o1", bot_in.ports["o2"])
    
    # Merged Output Section (Bottom half)
    bot_out = c << gf.components.straight(
        length=length_straight_out, 
        cross_section=xs_outer
    )
    bot_out.connect("o1", bot_bend.ports["o2"])

    # --- Ports ---
    c.add_port("o1_top", port=top_in.ports["o1"])
    c.add_port("o1_mid", port=center_in.ports["o1"])
    c.add_port("o1_bot", port=bot_in.ports["o1"])
    
    # Combined output port (Width = 1.0um)
    c.add_port(
        "o2",
        center=(length_total, 0),
        width=width_outer * 2,
        orientation=0,
        layer=layer_wg
    )

    return c

if __name__ == "__main__":
    device = trident_mode_converter()
    device.show()
    device.write_gds("trident_converter_final.gds")