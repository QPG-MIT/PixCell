import gdsfactory as gf

@gf.cell
def recreate_directional_coupler():
    """
    Refined directional coupler with optimized S-bends and thinner waveguides
    to better match the target visual proportions and the [120, 4] footprint.
    """
    c = gf.Component("directional_coupler_refined_v4")
    
    # --- Parameters ---
    total_length = 120.0
    total_height = 4.0
    
    # Slimmer waveguide width and tighter gap for better visual fidelity
    wg_width = 0.35 
    gap = 0.1
    
    # Adjusted length budget for smoother transitions:
    # 120um = Lead(5) + Sbend(35) + Coupling(40) + Sbend(35) + Lead(5)
    lead_length = 5.0
    sbend_dx = 35.0
    coupling_length = 40.0
    
    # Height Calculation:
    # Target outer edges are at +/- (total_height / 2) = +/- 2.0 um
    # Center-to-center separation at ends = total_height - wg_width = 3.65 um
    # Center-to-center separation at coupler = gap + wg_width = 0.45 um
    # Vertical offset (dy) for each S-bend arm = (3.65 - 0.45) / 2 = 1.6 um
    sbend_dy = 1.6
    
    # --- Cross Section ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # --- Component Primitives ---
    cp = gf.components.coupler_straight(length=coupling_length, gap=gap, cross_section=xs)
    sb = gf.components.bend_s(size=(sbend_dx, sbend_dy), cross_section=xs)
    lead = gf.components.straight(length=lead_length, cross_section=xs)
    
    # --- Assembly ---
    # Central coupling region anchor
    cp_ref = c << cp
    
    # LEFT SIDE
    # Top-Left: S-bend flares up + short lead
    sb_tl = c << sb
    sb_tl.mirror_y()
    sb_tl.connect("o2", cp_ref.ports["o2"])
    l_tl = c << lead
    l_tl.connect("o2", sb_tl.ports["o1"])
    
    # Bottom-Left: S-bend flares down + short lead
    sb_bl = c << sb
    sb_bl.connect("o2", cp_ref.ports["o1"])
    l_bl = c << lead
    l_bl.connect("o2", sb_bl.ports["o1"])
    
    # RIGHT SIDE
    # Top-Right: S-bend flares up + short lead
    sb_tr = c << sb
    sb_tr.connect("o1", cp_ref.ports["o3"])
    l_tr = c << lead
    l_tr.connect("o1", sb_tr.ports["o2"])
    
    # Bottom-Right: S-bend flares down + short lead
    sb_br = c << sb
    sb_br.mirror_y()
    sb_br.connect("o1", cp_ref.ports["o4"])
    l_br = c << lead
    l_br.connect("o1", sb_br.ports["o2"])
    
    # --- External Ports ---
    c.add_port("o1", port=l_bl.ports["o1"])
    c.add_port("o2", port=l_tl.ports["o1"])
    c.add_port("o3", port=l_tr.ports["o2"])
    c.add_port("o4", port=l_br.ports["o2"])
    
    return c

if __name__ == "__main__":
    component = recreate_directional_coupler()
    
    # Verification of final dimensions
    print(f"Component Width: {component.xsize:.2f} um (Constraint: 120.00)")
    print(f"Component Height: {component.ysize:.2f} um (Constraint: 4.00)")
    
    component.write_gds("directional_coupler_v4.gds")