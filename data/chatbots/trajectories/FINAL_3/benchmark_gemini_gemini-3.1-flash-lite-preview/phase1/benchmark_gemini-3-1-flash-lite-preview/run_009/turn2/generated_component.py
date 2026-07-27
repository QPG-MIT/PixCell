import gdsfactory as gf

@gf.cell
def coupler_parametric():
    """
    Creates a directional coupler using primitive connections.
    Total length: 120um
    Total height: 4um (y = +2.0 to y = -2.0)
    """
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Dimensions for 120um total length
    # 20 (in) + 20 (bend) + 20 (coupling) + 20 (bend) + 20 (out) = 120
    l_in_out = 20
    l_bend = 20
    l_coupling = 20
    
    # Vertical setup
    # Start at y = +/- 2.0
    # Converge to y = +/- 0.25 (total 0.5um gap)
    y_start = 2.0
    y_target = 0.25
    dy = y_start - y_target  # The vertical distance the S-bend must traverse

    def build_arm(side="top"):
        # Determine direction of bend (top moves down, bottom moves up)
        y_dir = -dy if side == "top" else dy
        
        # 1. Input Straight
        wg_in = c << gf.components.straight(length=l_in_out, cross_section=xs)
        # 2. Converging S-Bend
        bend1 = c << gf.components.bend_s(size=(l_bend, y_dir), cross_section=xs)
        bend1.connect("o1", wg_in.ports["o2"])
        # 3. Coupling Straight
        wg_coupling = c << gf.components.straight(length=l_coupling, cross_section=xs)
        wg_coupling.connect("o1", bend1.ports["o2"])
        # 4. Diverging S-Bend
        bend2 = c << gf.components.bend_s(size=(l_bend, -y_dir), cross_section=xs)
        bend2.connect("o1", wg_coupling.ports["o2"])
        # 5. Output Straight
        wg_out = c << gf.components.straight(length=l_in_out, cross_section=xs)
        wg_out.connect("o1", bend2.ports["o2"])
        
        return wg_in, wg_out

    # Build Top Arm (Starts at +2.0)
    top_in, top_out = build_arm(side="top")
    top_in.movey(y_start)

    # Build Bottom Arm (Starts at -2.0)
    bot_in, bot_out = build_arm(side="bottom")
    bot_in.movey(-y_start)

    return c

# Execute and save
if __name__ == "__main__":
    device = coupler_parametric()
    device.write_gds("coupler.gds")
    print("Successfully generated: coupler.gds")