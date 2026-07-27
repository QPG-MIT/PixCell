import gdsfactory as gf

@gf.cell
def symmetric_coupler_v3() -> gf.Component:
    """
    Symmetric coupler refined for Turn 3.
    Matches target image by sharpening S-bends and lengthening the coupling region.
    
    Total Footprint: 120 um x 4 um.
    """
    c = gf.Component("symmetric_coupler_v3")

    # 1. Global Dimensions
    W_TOTAL = 120.0
    H_TOTAL = 4.0
    
    wg_width = 0.5
    gap = 0.2  # Defined gap between waveguides in the center
    
    # Longitudinal distribution tuned for "snappier" transitions
    # Target proportions: short tails, compact bends, long center.
    l_end = 12.0    # Horizontal tails
    l_sbend = 18.0  # Transition length (sharper than previous 30um)
    l_center = W_TOTAL - 2 * l_end - 2 * l_sbend # 60.0 um
    
    # 2. Vertical Offset Calculations
    # We want to push the ports as far as possible within the 4um limit
    # Outer port centerlines (leaving a small 0.25um buffer from edges)
    y_outer = (H_TOTAL / 2) - (wg_width / 2) - 0.25
    # Inner coupling centerlines
    y_inner = (wg_width + gap) / 2
    # The vertical shift required for the S-bend
    dy = y_outer - y_inner 

    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 3. Component Assembly
    
    # Central Coupling Section (The "Bar")
    mid = c << gf.components.coupler_straight(length=l_center, gap=gap, cross_section=xs)

    # S-bends: (dx, dy)
    # Note: dy is positive for fan-out (moving away from center)
    
    # Left side transitions (connect "o2" which is input-facing to mid)
    sb_tl = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    sb_tl.connect("o2", mid.ports["o2"])
    
    sb_bl = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    sb_bl.connect("o2", mid.ports["o1"])
    
    # Right side transitions (connect "o1" which is input-facing to mid)
    sb_tr = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    sb_tr.connect("o1", mid.ports["o3"])
    
    sb_br = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    sb_br.connect("o1", mid.ports["o4"])

    # Port Tails (Straight segments)
    st_tl = c << gf.components.straight(length=l_end, cross_section=xs)
    st_tl.connect("o2", sb_tl.ports["o1"])
    
    st_bl = c << gf.components.straight(length=l_end, cross_section=xs)
    st_bl.connect("o2", sb_bl.ports["o1"])
    
    st_tr = c << gf.components.straight(length=l_end, cross_section=xs)
    st_tr.connect("o1", sb_tr.ports["o2"])
    
    st_br = c << gf.components.straight(length=l_end, cross_section=xs)
    st_br.connect("o1", sb_br.ports["o2"])

    # 4. Port Exposure
    c.add_port("o1", port=st_bl.ports["o1"])
    c.add_port("o2", port=st_tl.ports["o1"])
    c.add_port("o3", port=st_tr.ports["o2"])
    c.add_port("o4", port=st_br.ports["o2"])

    return c

if __name__ == "__main__":
    device = symmetric_coupler_v3()
    device.write_gds("symmetric_coupler_v3.gds")
    
    print(f"Device Name: {device.name}")
    print(f"Footprint: {device.xsize:.2f} um x {device.ysize:.2f} um")