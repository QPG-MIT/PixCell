import gdsfactory as gf

@gf.cell
def recreate_directional_coupler():
    """
    Directional coupler iteration V5:
    - Increased waveguide width to 1.3um to match visual 'thickness'.
    - Narrowed gap to 0.05um for a tighter coupling region.
    - Adjusted S-bend steepness and lengths to match target proportions.
    - Total Footprint: [120, 4]
    """
    c = gf.Component("directional_coupler_v5")
    
    # --- Parameters ---
    total_length = 120.0
    total_height = 4.0
    
    # Substantially thicker waveguides for better visual fidelity
    wg_width = 1.3 
    gap = 0.05
    
    # Center-to-center separation calculations:
    # At coupling region (center):
    s_mid = wg_width + gap # 1.35 um
    
    # At input/output ports (ends):
    # We want top edge at +2.0 and bottom edge at -2.0.
    # Center-to-center = total_height - wg_width
    s_ends = total_height - wg_width # 2.7 um
    
    # Vertical offset (dy) for each S-bend arm transition:
    # (s_ends - s_mid) / 2
    sbend_dy = (s_ends - s_mid) / 2 # 0.675 um
    
    # Horizontal length allocation:
    # total (120) = 2*lead + 2*sbend_dx + coupling_length
    lead_length = 5.0
    sbend_dx = 15.0 # Shorter transitions make the 'elbows' more pronounced
    coupling_length = total_length - 2 * (lead_length + sbend_dx) # 80.0 um
    
    # --- Cross Section ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # --- Component Primitives ---
    cp = gf.components.coupler_straight(length=coupling_length, gap=gap, cross_section=xs)
    sb = gf.components.bend_s(size=(sbend_dx, sbend_dy), cross_section=xs)
    lead = gf.components.straight(length=lead_length, cross_section=xs)
    
    # --- Assembly ---
    # Central coupling region
    cp_ref = c << cp
    
    # LEFT SIDE
    # Top-Left: S-bend + lead
    sb_tl = c << sb
    sb_tl.mirror_y()
    sb_tl.connect("o2", cp_ref.ports["o2"])
    l_tl = c << lead
    l_tl.connect("o2", sb_tl.ports["o1"])
    
    # Bottom-Left: S-bend + lead
    sb_bl = c << sb
    sb_bl.connect("o2", cp_ref.ports["o1"])
    l_bl = c << lead
    l_bl.connect("o2", sb_bl.ports["o1"])
    
    # RIGHT SIDE
    # Top-Right: S-bend + lead
    sb_tr = c << sb
    sb_tr.connect("o1", cp_ref.ports["o3"])
    l_tr = c << lead
    l_tr.connect("o1", sb_tr.ports["o2"])
    
    # Bottom-Right: S-bend + lead
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
    print(f"Final Component Width: {component.xsize:.2f} um (Target: 120.00)")
    print(f"Final Component Height: {component.ysize:.2f} um (Target: 4.00)")
    
    component.write_gds("directional_coupler_v5.gds")