import gdsfactory as gf

@gf.cell
def directional_coupler_reconstruction(
    width: float = 0.5,
    gap: float = 0.2,
    coupler_length: float = 40.0,
    bend_length: float = 30.0,
    ext_length: float = 10.0,
    bend_height: float = 1.4,
    layer: tuple[int, int] = (1, 0),
) -> gf.Component:
    """
    Recreates the directional coupler with symmetric horizontal extensions.
    
    Footprint Calculation:
    - Total Width: 10 (ext) + 30 (bend) + 40 (coupler) + 30 (bend) + 10 (ext) = 120 um
    - Total Height:
        Coupler centers: +/- 0.35 um
        S-bend offset: 1.4 um
        Port centers: +/- 1.75 um
        Total Height (edge-to-edge): 1.75 * 2 + 0.5 = 4.0 um
    """
    c = gf.Component()
    
    # Define cross section as per catalog Section 6
    xs = gf.cross_section.cross_section(width=width, layer=layer)

    # 1. Central Interaction Region
    # Ports: o1 (top-left), o2 (bot-left), o3 (bot-right), o4 (top-right)
    m = c << gf.components.coupler_straight(length=coupler_length, gap=gap, cross_section=xs)

    # 2. Define Primitives for Branches
    # S-bends move in +X. Connect logic handles orientation.
    # To flare OUT from coupler (y=0.35) to edge (y=1.75):
    # If connecting o1 to coupler: dy = 1.4
    # If connecting o2 to coupler: dy = -1.4
    s_up = gf.components.bend_s(size=(bend_length, bend_height), cross_section=xs)
    s_dn = gf.components.bend_s(size=(bend_length, -bend_height), cross_section=xs)
    ext = gf.components.straight(length=ext_length, cross_section=xs)

    # 3. Assemble Left Side (Input)
    # Top-Left: Connect S-bend o2 to coupler o1. Flare out means o1 is higher than o2.
    blt = c << s_dn
    blt.connect("o2", m.ports["o1"])
    elt = c << ext
    elt.connect("o2", blt.ports["o1"])

    # Bot-Left: Connect S-bend o2 to coupler o2. Flare out means o1 is lower than o2.
    blb = c << s_up
    blb.connect("o2", m.ports["o2"])
    elb = c << ext
    elb.connect("o2", blb.ports["o1"])

    # 4. Assemble Right Side (Output)
    # Top-Right: Connect S-bend o1 to coupler o4. Flare out means o2 is higher than o1.
    brt = c << s_up
    brt.connect("o1", m.ports["o4"])
    ert = c << ext
    ert.connect("o1", brt.ports["o2"])

    # Bot-Right: Connect S-bend o1 to coupler o3. Flare out means o2 is lower than o1.
    brb = c << s_dn
    brb.connect("o1", m.ports["o3"])
    erb = c << ext
    erb.connect("o1", brb.ports["o2"])

    # 5. Expose External Ports
    c.add_port("o1", port=elt.ports["o1"])
    c.add_port("o2", port=elb.ports["o1"])
    c.add_port("o3", port=erb.ports["o2"])
    c.add_port("o4", port=ert.ports["o2"])

    return c

if __name__ == "__main__":
    component = directional_coupler_reconstruction()
    
    # Print dimensions to verify footprint (120, 4)
    print(f"Device size: {component.xsize:.1f} um x {component.ysize:.1f} um")
    
    component.write_gds("coupler_corrected.gds")
    component.show()