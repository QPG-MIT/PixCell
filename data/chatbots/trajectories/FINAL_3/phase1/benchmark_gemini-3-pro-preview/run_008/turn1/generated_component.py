import gdsfactory as gf

@gf.cell
def directional_coupler_4x240():
    """
    Creates a directional coupler matching the image and footprint constraints.
    Footprint: 4um x 240um.
    """
    c = gf.Component()

    # =======================================================================
    # 1. Parameter Definition
    # =======================================================================
    # External Footprint Constraints
    total_length = 240.0
    total_height = 4.0      # Input/Output separation (edge-to-edge approx)
    
    # Internal Geometry Parameters
    wg_width = 0.5          # Standard waveguide width
    gap = 0.2               # Coupling gap (distance between waveguides in center)
    length_coupling = 80.0  # Length of the parallel straight section
    
    # Calculated Parameters
    # Length available for the S-bends (split between input and output)
    length_bend = (total_length - length_coupling) / 2
    
    # Y-coordinates calculation relative to center (y=0)
    # The ports are centered within the 4um box. 
    # Center y of input arm = (Total Height / 2) - (WG Width / 2)
    y_input_center = (total_height / 2) - (wg_width / 2)
    
    # Center y of coupled arm = (Gap / 2) + (WG Width / 2)
    y_coupled_center = (gap / 2) + (wg_width / 2)
    
    # The vertical distance (dy) the S-bend must travel
    dy = y_input_center - y_coupled_center

    # Cross Section Definition (from catalog)
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # =======================================================================
    # 2. Primitives Creation
    # =======================================================================
    
    # Input/Output Bends using 'bend_s' from catalog
    # Top bend needs to go DOWN (negative dy), Bottom bend needs to go UP (positive dy)
    bend_converge_top = gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    bend_converge_bot = gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    
    # Diverging bends (mirrored logic)
    bend_diverge_top = gf.components.bend_s(size=(length_bend, dy), cross_section=xs)
    bend_diverge_bot = gf.components.bend_s(size=(length_bend, -dy), cross_section=xs)
    
    # Straight coupling section
    straight_coupler = gf.components.straight(length=length_coupling, cross_section=xs)

    # =======================================================================
    # 3. Component Assembly
    # =======================================================================
    
    # --- Top Arm Construction ---
    # 1. Input S-Bend
    ref_ti = c << bend_converge_top
    ref_ti.move((0, y_input_center)) # Start at x=0, y=input height

    # 2. Straight Section
    ref_tm = c << straight_coupler
    ref_tm.connect("o1", ref_ti.ports["o2"])

    # 3. Output S-Bend
    ref_to = c << bend_diverge_top
    ref_to.connect("o1", ref_tm.ports["o2"])

    # --- Bottom Arm Construction ---
    # 1. Input S-Bend
    ref_bi = c << bend_converge_bot
    ref_bi.move((0, -y_input_center)) # Start at x=0, y=negative input height

    # 2. Straight Section
    ref_bm = c << straight_coupler
    ref_bm.connect("o1", ref_bi.ports["o2"])

    # 3. Output S-Bend
    ref_bo = c << bend_diverge_bot
    ref_bo.connect("o1", ref_bm.ports["o2"])

    # =======================================================================
    # 4. Expose Ports
    # =======================================================================
    c.add_port("o1", port=ref_ti.ports["o1"]) # Top Input
    c.add_port("o2", port=ref_bi.ports["o1"]) # Bottom Input
    c.add_port("o3", port=ref_to.ports["o2"]) # Top Output
    c.add_port("o4", port=ref_bo.ports["o2"]) # Bottom Output

    return c

# Create and save the GDS
device = directional_coupler_4x240()
device.write_gds("directional_coupler.gds")

# Optional: Visualize if running in a notebook/supported environment
device.show()