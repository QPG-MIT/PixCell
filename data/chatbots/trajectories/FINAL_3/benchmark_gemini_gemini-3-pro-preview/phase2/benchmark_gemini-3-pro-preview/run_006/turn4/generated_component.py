import gdsfactory as gf

@gf.cell
def directional_coupler_final():
    """
    Creates a directional coupler with optimized proportions to match the target image.
    
    Structure Definition:
    - Central coupling region: Parallel waveguides with narrow gap.
    - S-Bend transitions: Connect ports to the coupling region using adiabatic bends.
    - Port Leads: Straight sections at the input/output.
    
    Dimensions (Total 120um x 4um):
    - Lead Length: 20um (Straight)
    - Bend Length: 20um (S-Bend)
    - Coupler Length: 40um (Straight)
    - Total Length: 20 + 20 + 40 + 20 + 20 = 120um
    
    Vertical Positions:
    - Device Height: 4.0um
    - Waveguide Width: 0.5um
    - Coupling Gap: 0.2um
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    # Longitudinal Segmentation
    len_lead = 20.0      # Balanced with bend length for visual accuracy
    len_bend = 20.0
    len_coup = 40.0
    
    # Transverse Dimensions
    wg_width = 0.5
    gap = 0.2
    total_height = 4.0
    
    # Calculate Center Y positions
    # Inner Y: center of waveguide in coupling region
    y_inner = (gap + wg_width) / 2
    # Outer Y: center of waveguide at ports (half of total height minus half wg width)
    y_outer = (total_height / 2) - (wg_width / 2)
    # Bend vertical displacement magnitude
    dy = y_outer - y_inner

    # Cross section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Build Center (Coupling Region) ---
    # Create the two parallel straight waveguides in the center
    wg_coup_top = c << gf.components.straight(length=len_coup, cross_section=xs)
    wg_coup_bot = c << gf.components.straight(length=len_coup, cross_section=xs)
    
    # Move to correct vertical positions
    wg_coup_top.movey(y_inner)
    wg_coup_bot.movey(-y_inner)

    # --- 2. Build Left Side (Inputs) ---
    # We construct outwards from the central coupler to the ports.
    
    # -- Top Input --
    # S-Bend: Transitions from Outer(High) to Inner(Low). 
    # Since we connect o2 to the coupler (inner), o1 is the outer input.
    # Relative to o1, o2 is LOWER. Thus height change is negative.
    bend_in_top = c << gf.components.bend_s(size=(len_bend, -dy), cross_section=xs)
    bend_in_top.connect("o2", wg_coup_top.ports["o1"])
    
    # Straight Lead
    lead_in_top = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_in_top.connect("o2", bend_in_top.ports["o1"])

    # -- Bottom Input --
    # S-Bend: Transitions from Outer(Low) to Inner(High).
    # Relative to o1, o2 is HIGHER. Thus height change is positive.
    bend_in_bot = c << gf.components.bend_s(size=(len_bend, dy), cross_section=xs)
    bend_in_bot.connect("o2", wg_coup_bot.ports["o1"])
    
    # Straight Lead
    lead_in_bot = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_in_bot.connect("o2", bend_in_bot.ports["o1"])

    # --- 3. Build Right Side (Outputs) ---
    # We construct outwards from the central coupler to the ports.
    
    # -- Top Output --
    # S-Bend: Transitions from Inner(Low) to Outer(High).
    # Connect o1 to coupler. o2 is output.
    # Relative to o1, o2 is HIGHER. Positive height change.
    bend_out_top = c << gf.components.bend_s(size=(len_bend, dy), cross_section=xs)
    bend_out_top.connect("o1", wg_coup_top.ports["o2"])
    
    # Straight Lead
    lead_out_top = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_out_top.connect("o1", bend_out_top.ports["o2"])

    # -- Bottom Output --
    # S-Bend: Transitions from Inner(High) to Outer(Low).
    # Relative to o1, o2 is LOWER. Negative height change.
    bend_out_bot = c << gf.components.bend_s(size=(len_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_coup_bot.ports["o2"])
    
    # Straight Lead
    lead_out_bot = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_out_bot.connect("o1", bend_out_bot.ports["o2"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=lead_in_top.ports["o1"]) # Top Left
    c.add_port("o2", port=lead_in_bot.ports["o1"]) # Bottom Left
    c.add_port("o3", port=lead_out_top.ports["o2"]) # Top Right
    c.add_port("o4", port=lead_out_bot.ports["o2"]) # Bottom Right

    return c

# Generate and save the GDS
device = directional_coupler_final()
device.write_gds("directional_coupler_final.gds")