import gdsfactory as gf

@gf.cell
def recreate_directional_coupler():
    """
    Recreates the directional coupler with straight terminations to match the target.
    
    Footprint constraint: [120, 4]
    """
    c = gf.Component("directional_coupler_refined")
    
    # --- Parameters ---
    total_length = 120.0
    total_height = 4.0
    wg_width = 0.5 
    gap = 0.2      
    
    # Length budget: 120um = Lead(10) + Sbend(20) + Coupling(60) + Sbend(20) + Lead(10)
    lead_length = 10.0
    sbend_dx = 20.0
    coupling_length = 60.0
    
    # Height Calculation:
    # Target outer edges are at +/- (total_height / 2) = +/- 2.0 um
    # Center-to-center separation at ends = total_height - wg_width = 3.5 um
    # Center-to-center separation at coupler = gap + wg_width = 0.7 um
    # Required dy for each S-bend arm = (3.5 - 0.7) / 2 = 1.4 um
    sbend_dy = 1.4
    
    # --- Cross Section ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # --- Component Primitives ---
    # Central coupling region
    cp = gf.components.coupler_straight(length=coupling_length, gap=gap, cross_section=xs)
    # S-bend transition
    sb = gf.components.bend_s(size=(sbend_dx, sbend_dy), cross_section=xs)
    # Straight leads for horizontal ports
    lead = gf.components.straight(length=lead_length, cross_section=xs)
    
    # --- Assembly ---
    # 1. Place the central coupler
    cp_ref = c << cp
    
    # 2. LEFT SIDE
    # Top-Left: Sbend (mirrored to flare up) + Lead
    sb_tl = c << sb
    sb_tl.mirror_y()
    sb_tl.connect("o2", cp_ref.ports["o2"])
    l_tl = c << lead
    l_tl.connect("o2", sb_tl.ports["o1"])
    
    # Bottom-Left: Sbend (flares down) + Lead
    sb_bl = c << sb
    sb_bl.connect("o2", cp_ref.ports["o1"])
    l_bl = c << lead
    l_bl.connect("o2", sb_bl.ports["o1"])
    
    # 3. RIGHT SIDE
    # Top-Right: Sbend (flares up) + Lead
    sb_tr = c << sb
    sb_tr.connect("o1", cp_ref.ports["o3"])
    l_tr = c << lead
    l_tr.connect("o1", sb_tr.ports["o2"])
    
    # Bottom-Right: Sbend (mirrored to flare down) + Lead
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
    
    # Verification
    print(f"Component Width: {component.xsize:.2f} um (Target: 120.00)")
    print(f"Component Height: {component.ysize:.2f} um (Target: 4.00)")
    
    component.write_gds("directional_coupler_v3.gds")
    # component.show() # Uncomment to view in KLayout