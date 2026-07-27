import gdsfactory as gf
from gdsfactory.cross_section import Section

@gf.cell
def coupler_device_v2():
    """
    Refined reproduction of the waveguide coupler device.
    Adjustments: Thicker outer slabs, longer coupling region, uniform gaps.
    """
    c = gf.Component("Coupler_Refined")

    # --- Dimensions ---
    L_total = 120.0
    L_coupling = 60.0   # Increased from 40 to 60 to match visual proportions
    L_bend = (L_total - L_coupling) / 2
    
    # Feature sizes
    w_thin = 0.15       # Width of thin waveguides
    gap = 0.15          # Gap between waveguides (intra-bundle)
    pitch = w_thin + gap
    w_slab = 0.8        # Increased slab width (was 0.6) for heavier visual weight
    dy_bend = 1.5       # Vertical offset for the S-bends

    # --- 1. Define Cross-Sections ---

    # A. Central Bus (5 parallel lines)
    # 1 Core + 2 flanking pairs
    sections_center = []
    for i in [1, 2]:
        sections_center.append(Section(width=w_thin, offset=+i*pitch, layer=(1, 0)))
        sections_center.append(Section(width=w_thin, offset=-i*pitch, layer=(1, 0)))

    xs_center = gf.cross_section.cross_section(
        width=w_thin,
        layer=(1, 0),
        sections=sections_center
    )

    # B. Outer Arm (2 Thin Lines + 1 Thick Slab)
    # Defined relative to the innermost line (the "core")
    sections_arm = []
    
    # Line 2 (Thin)
    sections_arm.append(Section(width=w_thin, offset=pitch, layer=(1, 0)))
    
    # Line 3 (Thick Slab)
    # Calculate offset to maintain constant 'gap' spacing
    # Center_Slab = (Edge_of_Line2) + Gap + (Half_Slab_Width)
    # Edge_of_Line2 = pitch + w_thin/2
    offset_slab = (pitch + w_thin/2) + gap + (w_slab/2)
    sections_arm.append(Section(width=w_slab, offset=offset_slab, layer=(1, 0)))

    xs_arm = gf.cross_section.cross_section(
        width=w_thin, # Line 1 (Core)
        layer=(1, 0),
        sections=sections_arm
    )

    # --- 2. Construct Geometry ---

    # A. Central Bus
    bus = c << gf.components.straight(length=L_total, cross_section=xs_center)

    # B. Arm Path Sub-Component
    # Using bend_s for adiabatic-like transitions
    arm_path = gf.Component("Arm_Path_Refined")
    
    # 1. Input Bend (High to Low)
    b_in = arm_path << gf.components.bend_s(
        size=(L_bend, -dy_bend), 
        cross_section=xs_arm
    )
    
    # 2. Straight Coupling Section
    straight = arm_path << gf.components.straight(
        length=L_coupling, 
        cross_section=xs_arm
    )
    
    # 3. Output Bend (Low to High)
    b_out = arm_path << gf.components.bend_s(
        size=(L_bend, dy_bend), 
        cross_section=xs_arm
    )
    
    # Connect internal ports
    straight.connect("o1", b_in.ports["o2"])
    b_out.connect("o1", straight.ports["o2"])
    
    # Expose external ports for placement
    arm_path.add_port("o1", port=b_in.ports["o1"])

    # --- 3. Assembly ---

    # Calculate placement Y-coordinate
    # We align the "waist" (straight part) to the central bus with a specific gap
    y_bus_top_edge = 2 * pitch + w_thin/2
    coupling_gap = 0.20 # Reduced slightly to match intra-bundle gaps
    
    # Target Y for the innermost edge of the arm's core line
    # y_core_center - w_thin/2 = y_bus_top_edge + coupling_gap
    y_waist_center = y_bus_top_edge + coupling_gap + w_thin/2

    # Place Top Arm
    # The arm_path origin (0,0) is at the start of the input bend.
    # The straight waist is at y = -dy_bend relative to origin.
    # We want waist at y_waist_center.
    # origin_y - dy_bend = y_waist_center  =>  origin_y = y_waist_center + dy_bend
    top_arm = c << arm_path
    top_arm.y = y_waist_center + dy_bend

    # Place Bottom Arm (Mirrored)
    bot_arm = c << arm_path
    bot_arm.mirror(p1=(0,0), p2=(1,0))
    # For mirrored arm, waist is at y = +dy_bend relative to origin.
    # We want waist at -y_waist_center.
    # origin_y + dy_bend = -y_waist_center => origin_y = -y_waist_center - dy_bend
    bot_arm.y = -(y_waist_center + dy_bend)

    return c

if __name__ == "__main__":
    device = coupler_device_v2()
    device.write_gds("coupler_device_v2.gds")
    print("GDS file 'coupler_device_v2.gds' generated.")