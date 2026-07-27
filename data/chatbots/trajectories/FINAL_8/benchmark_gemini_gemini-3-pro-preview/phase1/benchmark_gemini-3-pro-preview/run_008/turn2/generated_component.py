import gdsfactory as gf

@gf.cell
def device_120_4():
    """
    Recreation of the symmetric waveguide structure with tapered wings.
    Footprint: 120um x 4um.
    """
    c = gf.Component()
    
    # --- Dimensions & Parameters ---
    total_width = 120.0
    total_height = 4.0
    layer_core = (1, 0)
    
    # Center Bus Parameters (5 lines)
    wg_width = 0.2
    wg_gap = 0.2
    n_wgs = 5
    
    # --- 1. Central Bus Construction ---
    # Calculate the vertical span of the central bus
    # Span = 5*0.2 + 4*0.2 = 1.8um
    center_span = n_wgs * wg_width + (n_wgs - 1) * wg_gap
    
    # Define the cross-section for the central waveguides
    xs_bus = gf.cross_section.cross_section(width=wg_width, layer=layer_core)
    
    # Create the straight waveguide component
    wg_straight = gf.components.straight(length=total_width, cross_section=xs_bus)
    
    # Array placement of the central waveguides
    # The array is centered at y=0. Calculate start y for the bottom-most wg.
    y_start = -center_span / 2 + wg_width / 2
    
    for i in range(n_wgs):
        ref = c << wg_straight
        ref.x = 0
        ref.y = y_start + i * (wg_width + wg_gap)

    # --- 2. Tapered Wing Construction ---
    # The wings are solid blocks with curved outer edges and internal slots.
    # CRITICAL FIX: The slots must not cut through the left/right edges.
    
    wing_to_bus_gap = 0.2
    # Calculate available height for one wing
    # Height = (4.0 - 1.8 - 2*0.2) / 2 = 0.9 um
    wing_height = (total_height - center_span - 2 * wing_to_bus_gap) / 2

    # A. Create the solid tapered body
    # Path is vertical (along Y). We extrude along this path while varying the width (X).
    p = gf.Path([(0, 0), (0, wing_height)])
    
    # Define CrossSections
    # Base (near center): Full width (120um)
    xs_base = gf.cross_section.cross_section(width=total_width, layer=layer_core)
    # Tip (outer edge): Narrower to create the inward curve profile (e.g., 112um)
    xs_tip = gf.cross_section.cross_section(width=total_width - 8.0, layer=layer_core)
    
    # Transition with sine profile for smooth curvature
    transition = gf.path.transition(xs_base, xs_tip, width_type='sine')
    
    # Extrude
    wing_solid = gf.path.extrude_transition(p, transition)
    
    # B. Create Slots (Negative space)
    # The slots must be shorter than the MINIMUM width of the wing (112um) to leave a rim.
    # We use length=106 to leave roughly 3um of solid rim on each side at the tip.
    slot_length = 106.0
    slot_height = 0.15
    slot_pitch = 0.25  # Tighter pitch to fit 3 slots within 0.9um height
    n_slots = 3
    slot_margin_y = 0.15 # Offset from the inner edge
    
    slots_layer = gf.Component()
    slot_rect = gf.components.rectangle(size=(slot_length, slot_height), layer=layer_core, centered=True)
    
    for i in range(n_slots):
        s = slots_layer << slot_rect
        s.x = 0
        s.y = slot_margin_y + i * slot_pitch + slot_height / 2
        
    # C. Boolean Operation: Cut slots from the solid wing
    wing_final = gf.boolean(wing_solid, slots_layer, operation="not", layer=layer_core)
    
    # --- 3. Final Assembly ---
    
    # Place Top Wing
    top_ref = c << wing_final
    # Position: ymin of wing aligns with the start of the wing area (above gap)
    top_ref.ymin = center_span / 2 + wing_to_bus_gap
    top_ref.x = 0
    
    # Place Bottom Wing (Mirrored)
    bot_ref = c << wing_final
    bot_ref.mirror(p1=(0,0), p2=(1,0)) # Mirror vertically across X-axis
    # Position: ymax of mirrored wing aligns with the start of the bottom wing area
    bot_ref.ymax = -(center_span / 2 + wing_to_bus_gap)
    bot_ref.x = 0
    
    return c

# Generate and Save
device = device_120_4()
device.write_gds("device_120_4.gds")