import gdsfactory as gf
from gdsfactory.cross_section import Section

@gf.cell
def coupler_device():
    """
    Reproduces the waveguide coupler device using parametric cross-sections
    and S-bends.
    """
    c = gf.Component("Coupler_Reproduced")

    # --- Dimensions derived from footprint (120um x 4um) & visual analysis ---
    L_total = 120.0
    L_coupling = 40.0   # Length of the central parallel region
    L_bend = (L_total - L_coupling) / 2  # Length of the S-bends
    
    # Feature sizes (approximate to fit 4um height)
    w_thin = 0.15       # Width of thin waveguides
    gap = 0.15          # Gap between waveguides
    pitch = w_thin + gap
    w_slab = 0.6        # Width of the thick outer slab on the arms
    dy_bend = 1.5       # Vertical offset for the S-bends

    # --- 1. Define Cross-Sections ---

    # A. Central Bus Cross-Section
    # Consists of 5 parallel lines centered at y=0
    # 1 center line (core) + 2 pairs of flanking sections
    sections_center = []
    for i in [1, 2]:
        # Add pairs of lines above and below
        sections_center.append(Section(width=w_thin, offset=+i*pitch, layer=(1, 0)))
        sections_center.append(Section(width=w_thin, offset=-i*pitch, layer=(1, 0)))

    xs_center = gf.cross_section.cross_section(
        width=w_thin,   # Center core width
        layer=(1, 0),
        sections=sections_center
    )

    # B. Outer Arm Cross-Section
    # Looks like: [Thin Line] [Gap] [Thin Line] [Gap] [Thick Slab]
    # We define this relative to the innermost edge facing the bus
    sections_arm = []
    
    # Second thin line (1st is the core defined in width=w_thin)
    sections_arm.append(Section(width=w_thin, offset=1*pitch, layer=(1, 0)))
    
    # Outer thick slab
    # Offset calculation: 2 pitches out, plus adjustment for the wider slab center
    offset_slab = 2*pitch + (w_slab - w_thin)/2
    sections_arm.append(Section(width=w_slab, offset=offset_slab, layer=(1, 0)))

    xs_arm = gf.cross_section.cross_section(
        width=w_thin, # Innermost line width
        layer=(1, 0),
        sections=sections_arm
    )

    # --- 2. Construct Components ---

    # A. Place Central Bus
    # A single straight waveguide carrying the composite cross-section
    bus = c << gf.components.straight(length=L_total, cross_section=xs_center)

    # B. Construct the Top Arm Path
    # The arm is an S-bend down -> Straight -> S-bend up
    arm_path = gf.Component("Arm_Path")
    
    # 1. Bend down (Input)
    # size=(x, y). y is negative to move closer to center.
    b_in = arm_path << gf.components.bend_s(
        size=(L_bend, -dy_bend), 
        cross_section=xs_arm
    )
    
    # 2. Straight coupling region
    straight = arm_path << gf.components.straight(
        length=L_coupling, 
        cross_section=xs_arm
    )
    
    # 3. Bend up (Output)
    b_out = arm_path << gf.components.bend_s(
        size=(L_bend, dy_bend), 
        cross_section=xs_arm
    )
    
    # Connect arm segments
    straight.connect("o1", b_in.ports["o2"])
    b_out.connect("o1", straight.ports["o2"])
    
    # Expose ports for the arm sub-component for easier placement (optional but good practice)
    arm_path.add_port("o1", port=b_in.ports["o1"])
    arm_path.add_port("o2", port=b_out.ports["o2"])

    # --- 3. Assembly ---

    # Calculate Y-position for the straight part of the arm
    # Top of central bus = 2 * pitch + w_thin/2
    y_center_max = 2 * pitch + w_thin/2
    coupling_gap = 0.25
    
    # The arm's "core" is its innermost line.
    # We want bottom of arm's core = Top of bus + gap
    # y_arm_core - w_thin/2 = y_center_max + coupling_gap
    y_waist_target = y_center_max + coupling_gap + w_thin/2

    # Place Top Arm
    # The arm_path origin is at the START of the S-bend.
    # The straight part is vertically offset by -dy_bend relative to the start.
    # So: y_waist = y_origin - dy_bend  ->  y_origin = y_waist + dy_bend
    top_arm = c << arm_path
    top_arm.y = y_waist_target + dy_bend

    # Place Bottom Arm
    # Mirror the arm_path vertically
    bot_arm = c << arm_path
    bot_arm.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis
    # Coordinate math for mirrored part:
    # Mirrored straight part is at y_origin + dy_bend (flipped sign).
    # We want it at -y_waist_target.
    # -y_waist = y_origin + dy_bend -> y_origin = -y_waist - dy_bend
    bot_arm.y = -(y_waist_target + dy_bend)

    return c

# Create the device and save to GDS
if __name__ == "__main__":
    device = coupler_device()
    device.write_gds("coupler_device.gds")
    print("GDS file 'coupler_device.gds' generated successfully.")