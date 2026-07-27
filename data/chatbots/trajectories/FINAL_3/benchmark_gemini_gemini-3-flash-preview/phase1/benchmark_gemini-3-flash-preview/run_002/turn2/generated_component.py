import gdsfactory as gf

@gf.cell
def symmetric_coupler_refined() -> gf.Component:
    """
    Refined symmetric coupler to match the proportions of the original image.
    Adjusts segment lengths and S-bend spans for a more graceful, balanced look.
    Total Footprint: 120 um x 4 um.
    """
    c = gf.Component("symmetric_coupler_refined")

    # 1. Footprint and Global Parameters
    W_TOTAL = 120.0
    H_TOTAL = 4.0
    
    # We slightly reduce the total vertical spread of the ports (from 4.0 to 3.6)
    # to match the visual whitespace seen in the target silhouette.
    active_height = 3.6 
    wg_width = 0.5
    gap = 0.15  # Slightly narrower gap for a sleeker central region
    
    # Longitudinal distribution: 120 = 5(end) + 30(sbend) + 50(center) + 30(sbend) + 5(end)
    # This significantly lengthens the transitions compared to the previous version.
    l_end = 5.0
    l_sbend = 30.0
    l_center = W_TOTAL - 2 * l_end - 2 * l_sbend # 50.0 um

    # 2. Offset Calculations for the fan-out
    # Centerline at the ports
    y_outer = (active_height / 2) - (wg_width / 2)
    # Centerline at the coupling region
    y_inner = (wg_width + gap) / 2
    # Vertical shift required for each arm
    dy = y_outer - y_inner 

    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 3. Component Assembly
    
    # Central Coupling Section
    mid = c << gf.components.coupler_straight(length=l_center, gap=gap, cross_section=xs)

    # Elongated S-bends (30um horizontal for ~1.2um vertical creates a very smooth curve)
    # Left transitions
    sb_tl = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    sb_tl.connect("o2", mid.ports["o2"])
    
    sb_bl = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    sb_bl.connect("o2", mid.ports["o1"])
    
    # Right transitions
    sb_tr = c << gf.components.bend_s(size=(l_sbend, dy), cross_section=xs)
    sb_tr.connect("o1", mid.ports["o3"])
    
    sb_br = c << gf.components.bend_s(size=(l_sbend, -dy), cross_section=xs)
    sb_br.connect("o1", mid.ports["o4"])

    # Shortened Straight Port Tails
    st_tl = c << gf.components.straight(length=l_end, cross_section=xs)
    st_tl.connect("o2", sb_tl.ports["o1"])
    
    st_bl = c << gf.components.straight(length=l_end, cross_section=xs)
    st_bl.connect("o2", sb_bl.ports["o1"])
    
    st_tr = c << gf.components.straight(length=l_end, cross_section=xs)
    st_tr.connect("o1", sb_tr.ports["o2"])
    
    st_br = c << gf.components.straight(length=l_end, cross_section=xs)
    st_br.connect("o1", sb_br.ports["o2"])

    # Expose final ports
    c.add_port("o1", port=st_bl.ports["o1"])
    c.add_port("o2", port=st_tl.ports["o1"])
    c.add_port("o3", port=st_tr.ports["o2"])
    c.add_port("o4", port=st_br.ports["o2"])

    return c

if __name__ == "__main__":
    device = symmetric_coupler_refined()
    device.write_gds("symmetric_coupler_refined.gds")
    
    # Display dimensions to confirm footprint compliance
    print(f"Refined Device: {device.name}")
    print(f"Final Footprint: {device.xsize:.2f} um x {device.ysize:.2f} um")