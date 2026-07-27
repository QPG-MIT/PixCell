import gdsfactory as gf

@gf.cell
def directional_coupler_final():
    """
    Creates a directional coupler matching the provided reference image.
    
    Structure Definition:
    - Central coupling region: Parallel waveguides with narrow gap.
    - S-Bend transitions: Connect ports to the coupling region.
    - Port Leads: Straight sections at the input/output to match the 'flat' entry seen in the target.
    
    Dimensions (Total 120um x 4um):
    - Lengths: Lead (15um) + Bend (25um) + Coupler (40um) + Bend (25um) + Lead (15um) = 120um.
    - Vertical: Ports at +/- 1.75um (center), Coupler at +/- 0.35um (center).
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    # Longitudinal Segmentation
    len_lead = 15.0      # Straight section at ports
    len_bend = 25.0      # S-bend transition
    len_coup = 40.0      # Central coupling region
    
    # Transverse Dimensions
    wg_width = 0.5
    gap = 0.2
    total_height = 4.0
    
    # Calculate Center Y positions
    # Inner Y: center of waveguide in coupling region (distance from y=0)
    y_inner = (gap + wg_width) / 2
    # Outer Y: center of waveguide at ports (distance from y=0)
    # Bounded by total_height/2 -> 2.0. Center is 2.0 - width/2
    y_outer = (total_height / 2) - (wg_width / 2)
    # Bend vertical displacement
    dy = y_outer - y_inner

    # Cross section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Build Center (Coupling Region) ---
    # Create coupling waveguides
    wg_coup_top = c << gf.components.straight(length=len_coup, cross_section=xs)
    wg_coup_bot = c << gf.components.straight(length=len_coup, cross_section=xs)
    
    # Move to vertical position
    wg_coup_top.movey(y_inner)
    wg_coup_bot.movey(-y_inner)

    # --- 2. Build Left Side (Inputs) ---
    # Top Input Branch: Lead -> Bend -> Coupler
    # We attach components outwards from the central coupler to ensure perfect alignment.
    
    # Top Left Bend: Transitions from High (Lead) to Low (Coupler)
    # Since we connect 'o2' to the coupler, 'o1' (start) is higher.
    # Relative vector o2 - o1 = (len, -dy) implies o1 is higher.
    bend_in_top = c << gf.components.bend_s(size=(len_bend, -dy), cross_section=xs)
    bend_in_top.connect("o2", wg_coup_top.ports["o1"])
    
    # Top Left Lead: Straight entering the bend
    lead_in_top = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_in_top.connect("o2", bend_in_top.ports["o1"])

    # Bottom Input Branch
    # Bottom Left Bend: Transitions from Low (Lead) to High (Coupler)
    # Relative vector o2 - o1 = (len, dy) implies o1 is lower.
    bend_in_bot = c << gf.components.bend_s(size=(len_bend, dy), cross_section=xs)
    bend_in_bot.connect("o2", wg_coup_bot.ports["o1"])
    
    # Bottom Left Lead
    lead_in_bot = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_in_bot.connect("o2", bend_in_bot.ports["o1"])

    # --- 3. Build Right Side (Outputs) ---
    # Top Output Branch: Coupler -> Bend -> Lead
    
    # Top Right Bend: Transitions from Low (Coupler) to High (Lead)
    # Connect 'o1' to coupler. 'o2' is higher.
    bend_out_top = c << gf.components.bend_s(size=(len_bend, dy), cross_section=xs)
    bend_out_top.connect("o1", wg_coup_top.ports["o2"])
    
    # Top Right Lead
    lead_out_top = c << gf.components.straight(length=len_lead, cross_section=xs)
    lead_out_top.connect("o1", bend_out_top.ports["o2"])

    # Bottom Output Branch
    # Bottom Right Bend: Transitions from High (Coupler) to Low (Lead)
    bend_out_bot = c << gf.components.bend_s(size=(len_bend, -dy), cross_section=xs)
    bend_out_bot.connect("o1", wg_coup_bot.ports["o2"])
    
    # Bottom Right Lead
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