import gdsfactory as gf

@gf.cell
def recreate_directional_coupler():
    """
    Recreates the directional coupler from the image using parametric primitives.
    
    Footprint constraint: [120, 4]
    - Total Length: 120 um
    - Total Height: 4 um
    """
    c = gf.Component("directional_coupler")
    
    # --- Parameters ---
    total_length = 120.0
    total_height = 4.0
    
    wg_width = 0.5 
    gap = 0.2      
    
    # Length allocation: [30 (S-bend) | 60 (Straight) | 30 (S-bend)] = 120 um
    coupling_length = 60.0
    sbend_dx = 30.0
    
    # Height calculation for 4um footprint:
    # center-to-center separation at coupling region = gap + wg_width = 0.7 um
    # outer edge of middle waveguides = (gap + wg_width)/2 + wg_width/2 = 0.6 um
    # target outer edge at ends = total_height / 2 = 2.0 um
    # required vertical shift (dy) for each S-bend arm = 2.0 - 0.6 = 1.4 um
    sbend_dy = 1.4
    
    # --- Cross Section ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # --- Primitives ---
    # Central coupling region
    # Ports: o1 (bot-left), o2 (top-left), o3 (top-right), o4 (bot-right)
    cp = gf.components.coupler_straight(length=coupling_length, gap=gap, cross_section=xs)
    
    # S-bend arms (Ports: o1, o2). Default dy is positive (upwards from o1 to o2)
    sbend = gf.components.bend_s(size=(sbend_dx, sbend_dy), cross_section=xs)
    
    # --- Assembly ---
    # Add the central straight coupler
    cp_ref = c << cp
    
    # --- LEFT SIDE (Connecting to ports o1/o2 of coupler) ---
    # Top-Left: Should flare UP to the left. 
    # Connect o2 (right end) of a mirrored-y sbend to cp.o2.
    sl_top = c << sbend
    sl_top.mirror_y() 
    sl_top.connect("o2", cp_ref.ports["o2"])
    
    # Bottom-Left: Should flare DOWN to the left.
    # Connect o2 (right end) of a standard sbend to cp.o1.
    sl_bot = c << sbend
    sl_bot.connect("o2", cp_ref.ports["o1"])
    
    # --- RIGHT SIDE (Connecting to ports o3/o4 of coupler) ---
    # Top-Right: Should flare UP to the right.
    # Connect o1 (left end) of a standard sbend to cp.o3.
    sr_top = c << sbend
    sr_top.connect("o1", cp_ref.ports["o3"])
    
    # Bottom-Right: Should flare DOWN to the right.
    # Connect o1 (left end) of a mirrored-y sbend to cp.o4.
    sr_bot = c << sbend
    sr_bot.mirror_y()
    sr_bot.connect("o1", cp_ref.ports["o4"])
    
    # --- External Ports ---
    c.add_port("o1", port=sl_bot.ports["o1"])
    c.add_port("o2", port=sl_top.ports["o1"])
    c.add_port("o3", port=sr_top.ports["o2"])
    c.add_port("o4", port=sr_bot.ports["o2"])
    
    return c

if __name__ == "__main__":
    component = recreate_directional_coupler()
    
    # Verify dimensions for constraints
    print(f"Component Width: {component.xsize:.2f} um (Target: 120.00)")
    print(f"Component Height: {component.ysize:.2f} um (Target: 4.00)")
    
    # Save the corrected geometry
    component.write_gds("directional_coupler_fixed.gds")