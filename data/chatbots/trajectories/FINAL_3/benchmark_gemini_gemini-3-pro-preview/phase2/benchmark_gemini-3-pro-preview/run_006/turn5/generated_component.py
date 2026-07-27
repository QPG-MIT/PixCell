import gdsfactory as gf

@gf.cell
def directional_coupler_final():
    """
    Creates a directional coupler matching the visual proportions of the target image.
    
    Adjustments from previous iteration:
    1. Increased waveguide width to 0.6um to match the visual 'weight' of the lines in the target image.
    2. Adjusted longitudinal segmentation: Shorter leads (15um) and longer bends (25um)
       to create a smoother, more 'flowy' S-bend transition as seen in the target, while maintaining total length.
    3. Maintained the tight coupling gap of 0.2um which provides the correct visual contrast in the center.
    
    Dimensions (Total 120um x 4um):
    - Lead Length: 15um
    - Bend Length: 25um
    - Coupler Length: 40um
    - Total Length: 15 + 25 + 40 + 25 + 15 = 120um
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    # Longitudinal Segmentation
    len_lead = 15.0     # Shorter leads (15um) to match target visual
    len_bend = 25.0     # Longer bends (25um) for smoother transition
    len_coup = 40.0     # Central coupling region (40um)
    
    # Transverse Dimensions
    wg_width = 0.6      # Increased width (0.6um) for visual fidelity
    gap = 0.2           # Tight coupling gap
    total_height = 4.0  # Footprint height constraint
    
    # Calculate Center Y positions
    # Inner Y: center of waveguide in coupling region
    # Distance from y=0 to center of top waveguide
    y_inner = (gap + wg_width) / 2
    
    # Outer Y: center of waveguide at ports
    # Total height is edge-to-edge. Center is (Total/2) - (Width/2)
    y_outer = (total_height / 2) - (wg_width / 2)
    
    # Bend vertical displacement magnitude
    dy = y_outer - y_inner

    # Cross section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Build Center (Coupling Region) ---
    wg_coup_top = c << gf.components.straight(length=len_coup, cross_section=xs)
    wg_coup_bot = c << gf.components.straight(length=len_coup, cross_section=xs)
    
    wg_coup_top.movey(y_inner)
    wg_coup_bot.movey(-y_inner)

    # --- 2. Build Left Side (Inputs) ---
    # Top Input: Outer(High) -> Inner(Low). Connect o2 to coupler.
    # Height change from o1 to o2 is NEGATIVE (High to Low)
    bend_in_top = c << gf.components.bend_s(size=(len_bend, -dy), cross_section=xs)
    bend_in_top.connect("o2", wg_coup_top.ports["o1"])
    
    lead_in_top = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_in_top.connect("o2", bend_in_top.ports["o1"])

    # Bottom Input: Outer(Low) -> Inner(High). Connect o2 to coupler.
    # Height change from o1 to o2 is POSITIVE (Low to High)
    bend_in_bot = c << gf.components.bend_s(size=(len_bend, dy), cross_section=xs)
    bend_in_bot.connect("o2", wg_coup_bot.ports["o1"])
    
    lead_in_bot = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_in_bot.connect("o2", bend_in_bot.ports["o1"])

    # --- 3. Build Right Side (Outputs) ---
    # Top Output: Inner(Low) -> Outer(High). Connect o1 to coupler.
    # Height change from o1 to o2 is POSITIVE (Low to High)
    bend_out_top = c << gf.components.bend_s(size=(len_bend, dy), cross_section=xs)
    bend_out_top.connect("o1", wg_coup_top.ports["o2"])
    
    lead_out_top = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_out_top.connect("o1", bend_out_top.ports["o2"])

    # Bottom Output: Inner(High) -> Outer(Low). Connect o1 to coupler.
    # Height change from o1 to o2 is NEGATIVE (High to Low)
    bend_out_bot = c << gf.components.bend_s(size=(len_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_coup_bot.ports["o2"])
    
    lead_out_bot = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_out_bot.connect("o1", bend_out_bot.ports["o2"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=lead_in_top.ports["o1"])
    c.add_port("o2", port=lead_in_bot.ports["o1"])
    c.add_port("o3", port=lead_out_top.ports["o2"])
    c.add_port("o4", port=lead_out_bot.ports["o2"])

    return c

# Generate and save the GDS
device = directional_coupler_final()
device.write_gds("directional_coupler_final.gds")