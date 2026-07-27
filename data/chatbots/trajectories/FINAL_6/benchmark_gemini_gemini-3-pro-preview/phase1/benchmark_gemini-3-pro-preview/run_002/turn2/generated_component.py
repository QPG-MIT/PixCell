import gdsfactory as gf

@gf.cell
def star_geometry_fixed():
    """
    Creates a 4-arm star device with smooth leaf-shaped lobes.
    Uses 'extrude_transition' with a 'sine' profile to ensure smooth curvature
    and fixes the validation error by strictly using catalog primitives.
    
    Footprint: 4.7um x 4.7um
    """
    c = gf.Component()

    # --- 1. Define Dimensions ---
    # Total Radius = 2.35um (Footprint 4.7um)
    # Stem: The straight section at the tip
    L_stem = 0.5
    
    # Lobe: The curved leaf section
    # We split it into two halves: Expansion and Contraction
    L_lobe_total = 1.85
    L_half = L_lobe_total / 2

    # Widths
    W_min = 0.2    # Width at center and stem
    W_max = 0.85   # Peak width of the lobe
    
    layer = (1, 0)

    # --- 2. Define Cross Sections and Transitions ---
    # Create base cross-sections
    xs_min = gf.cross_section.cross_section(width=W_min, layer=layer)
    xs_max = gf.cross_section.cross_section(width=W_max, layer=layer)

    # Define Transitions using 'sine' profile for smoothness
    # Transition 1: Expand from Min to Max (Concave Up -> Concave Down)
    t_expand = gf.path.transition(xs_min, xs_max, width_type='sine')
    
    # Transition 2: Contract from Max to Min (Concave Down -> Concave Up)
    t_contract = gf.path.transition(xs_max, xs_min, width_type='sine')

    # --- 3. Construct One Arm ---
    arm = gf.Component("Arm")

    # Segment A: Expansion
    p_expand = gf.path.straight(length=L_half)
    # extrude_transition creates a component
    seg_expand = gf.path.extrude_transition(p_expand, t_expand)
    ref_expand = arm << seg_expand

    # Segment B: Contraction
    p_contract = gf.path.straight(length=L_half)
    seg_contract = gf.path.extrude_transition(p_contract, t_contract)
    ref_contract = arm << seg_contract

    # Segment C: Stem (Constant width)
    seg_stem = gf.components.straight(length=L_stem, cross_section=xs_min)
    ref_stem = arm << seg_stem

    # --- 4. Connect Segments ---
    # Connect Expansion -> Contraction -> Stem
    ref_contract.connect("o1", ref_expand.ports["o2"])
    ref_stem.connect("o1", ref_contract.ports["o2"])

    # Expose the input port at the base (start of expansion)
    arm.add_port("o1", port=ref_expand.ports["o1"])

    # --- 5. Assemble the Star ---
    # Rotate and place 4 arms at the center
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
        # All arms originate from (0,0) due to rotation around origin

    return c

# Create and save the device
device = star_geometry_fixed()
device.write_gds("star_geometry_fixed.gds")