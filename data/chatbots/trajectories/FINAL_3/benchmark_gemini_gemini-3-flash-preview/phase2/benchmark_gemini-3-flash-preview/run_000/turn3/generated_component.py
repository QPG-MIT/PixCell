import gdsfactory as gf

@gf.cell
def directional_coupler_reconstruction(
    width: float = 0.5,
    gap: float = 0.4,
    coupler_length: float = 60.0,
    bend_length: float = 20.0,
    ext_length: float = 10.0,
    layer: tuple[int, int] = (1, 0),
) -> gf.Component:
    """
    Directional coupler matching the target image proportions and footprint.
    
    Footprint Calculation:
    - Total Width: 10 (ext) + 20 (bend) + 60 (coupler) + 20 (bend) + 10 (ext) = 120 um
    - Total Height:
        Port centers are at +/- 1.75 um. 
        Top edge = 1.75 + 0.25 = 2.0 um
        Bottom edge = -1.75 - 0.25 = -2.0 um
        Total Height = 4.0 um
    """
    c = gf.Component()
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=width, layer=layer)

    # 1. Central Interaction Region
    # Coupler centers waveguides at +/- (gap/2 + width/2) = +/- 0.45 um
    m = c << gf.components.coupler_straight(length=coupler_length, gap=gap, cross_section=xs)

    # 2. Define S-bend and extension
    # Target port center is 1.75. Coupler port center is 0.45.
    # Required vertical shift (dy) = 1.75 - 0.45 = 1.3 um
    bend_height = 1.3
    
    # We create standard s-bends. npoints increased for smoothness.
    s_up = gf.components.bend_s(size=(bend_length, bend_height), cross_section=xs, npoints=200)
    s_dn = gf.components.bend_s(size=(bend_length, -bend_height), cross_section=xs, npoints=200)
    ext = gf.components.straight(length=ext_length, cross_section=xs)

    # 3. Assemble Left Side (Input)
    # Top-Left Branch
    blt = c << s_dn
    blt.connect("o2", m.ports["o1"])
    elt = c << ext
    elt.connect("o2", blt.ports["o1"])

    # Bot-Left Branch
    blb = c << s_up
    blb.connect("o2", m.ports["o2"])
    elb = c << ext
    elb.connect("o2", blb.ports["o1"])

    # 4. Assemble Right Side (Output)
    # Top-Right Branch
    brt = c << s_up
    brt.connect("o1", m.ports["o4"])
    ert = c << ext
    ert.connect("o1", brt.ports["o2"])

    # Bot-Right Branch
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
    # The parameters are tuned to match the 120x4 footprint and visual style
    component = directional_coupler_reconstruction()
    
    # Verification of footprint
    print(f"Final Device Dimensions: {component.xsize:.1f} um x {component.ysize:.1f} um")
    
    component.write_gds("coupler_v3.gds")
    component.show()