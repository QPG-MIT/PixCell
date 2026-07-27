import gdsfactory as gf

@gf.cell
def swg_coupler():
    """
    Recreation of the SWG/Multi-waveguide coupler based on the provided image.
    Footprint constraint: 120um x 4um.
    """
    c = gf.Component()

    # ==========================================
    # Parameters
    # ==========================================
    # Dimensions derived from 120x4 footprint
    l_total = 120
    l_interaction = 60
    l_bend = (l_total - l_interaction) / 2  # 30um
    
    # Widths estimated from image contrast
    w_main = 0.5
    w_thin = 0.15
    
    # Y-coordinates
    # Total height 4um implies edges are at +2 and -2.
    # Center of outer ports approx at 1.75 (2 - 0.5/2)
    y_port_offset = 1.75
    
    # Inner interaction region spacing
    y_main_inner = 0.7  # Main waveguides in the center
    gap_spacing = 0.25  # Pitch of thin lines
    
    # Calculate S-bend height difference (dy)
    # Bend goes from inner Y to outer Y
    dy = y_port_offset - y_main_inner

    # ==========================================
    # 1. Center Interaction Region
    # ==========================================
    
    # Main Top and Bottom Straights
    # We use a cross_section specific to the main waveguides
    xs_main = gf.cross_section.cross_section(width=w_main, layer=(1, 0))
    
    wg_top = c << gf.components.straight(length=l_interaction, cross_section=xs_main)
    wg_bot = c << gf.components.straight(length=l_interaction, cross_section=xs_main)
    
    wg_top.movey(y_main_inner)
    wg_bot.movey(-y_main_inner)
    
    # Floating Thin Rails in the gap
    # Image shows 3 distinct thin lines between the main blocks
    xs_thin = gf.cross_section.cross_section(width=w_thin, layer=(1, 0))
    
    # Create 3 rails centered at 0, +pitch, -pitch
    rail_offsets = [0, gap_spacing, -gap_spacing]
    
    for offset in rail_offsets:
        rail = c << gf.components.straight(length=l_interaction, cross_section=xs_thin)
        rail.movey(offset)

    # ==========================================
    # 2. Input/Output S-Bends
    # ==========================================
    
    # Using parametric component: bend_s
    # Size takes (length, height_change). 
    # Positive height_change goes UP.
    
    # --- Top Left Input ---
    # Needs to go from High (Input) to Low (Center).
    # This is a Down-Right movement relative to flow.
    # bend_s (L, H) is Up-Right. We mirror Y to get Down-Right.
    bend_tl = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs_main)
    bend_tl.mirror_y()
    bend_tl.connect("o2", wg_top.ports["o1"]) # Connect output of bend to input of straight
    
    # --- Bottom Left Input ---
    # Needs to go from Low (Input) to High (Center).
    # This is Up-Right movement. Standard bend_s.
    bend_bl = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs_main)
    bend_bl.connect("o2", wg_bot.ports["o1"])
    
    # --- Top Right Output ---
    # Needs to go from Low (Center) to High (Output).
    # This is Up-Right movement. Standard bend_s.
    bend_tr = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs_main)
    bend_tr.connect("o1", wg_top.ports["o2"])
    
    # --- Bottom Right Output ---
    # Needs to go from High (Center) to Low (Output).
    # This is Down-Right movement. Mirror Y.
    bend_br = c << gf.components.bend_s(size=(l_bend, dy), cross_section=xs_main)
    bend_br.mirror_y()
    bend_br.connect("o1", wg_bot.ports["o2"])

    # ==========================================
    # Ports
    # ==========================================
    c.add_port("o1", port=bend_tl.ports["o1"])
    c.add_port("o2", port=bend_bl.ports["o1"])
    c.add_port("o3", port=bend_tr.ports["o2"])
    c.add_port("o4", port=bend_br.ports["o2"])

    return c

# Generate and Save
device = swg_coupler()
device.write_gds("swg_coupler.gds")

# Optional: Visualize if running in notebook
# device.plot()