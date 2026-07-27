import gdsfactory as gf

@gf.cell
def device_structure():
    """
    Constructs a racetrack resonator with variable arm width and internal slots.
    
    Geometry breakdown based on target image:
    1. Outer Hull: Fixed stadium shape (5.5um x 3.0um).
    2. Inner Void: A 'bulging' polygon. 
       - Center: Wide void (creating thin arms).
       - Ends: Narrow void (creating thick bends).
       - Transition: Linear taper connecting the two.
    3. Slots: Rectangular cutouts placed within the thin arm sections.
    """
    c = gf.Component()

    # --- Dimensions ---
    # Footprint constraint: 3.0um x 5.5um
    width = 5.5
    height = 3.0
    
    # Outer geometry
    r_outer = height / 2.0        # 1.5um
    l_straight = width - 2 * r_outer  # 2.5um
    layer = (1, 0)

    # --- Internal Geometry Parameters ---
    # Bends are thick -> Inner radius is small relative to outer radius
    r_inner = 0.55
    
    # Straight arms are thin -> Inner void is wide in the center
    # Arm width in the straight section is set to 0.5um
    arm_width_straight = 0.5
    h_void_center = height - 2 * arm_width_straight  # 2.0um (Wide void)
    
    # Void height at the ends matches the inner bend diameter
    h_void_ends = 2 * r_inner  # 1.1um (Narrow void)
    
    # Longitudinal Breakdown of the straight section (Total 2.5um)
    # The void consists of: Taper -> Constant Width -> Taper
    l_taper = 0.5
    l_constant = l_straight - 2 * l_taper  # 1.5um (Space for slots)

    # Slot parameters (Holes in the arms)
    slot_len = 0.5
    slot_height = 0.25
    slot_gap = 0.2

    # --- 1. Create Outer Hull (Stadium) ---
    outer = gf.Component()
    
    # Central rectangle
    outer << gf.components.rectangle(
        size=(l_straight, height), 
        layer=layer, 
        centered=True
    )
    
    # End circles
    c_right = outer << gf.components.circle(radius=r_outer, layer=layer)
    c_right.movex(l_straight / 2.0)
    
    c_left = outer << gf.components.circle(radius=r_outer, layer=layer)
    c_left.movex(-l_straight / 2.0)

    # --- 2. Create Inner Void (Negative Space) ---
    void = gf.Component()
    
    # 2a. Central wide rectangle (between the tapers)
    # This defines the region where the arms are thinnest
    void_center = void << gf.components.rectangle(
        size=(l_constant, h_void_center),
        layer=layer,
        centered=True
    )
    
    # 2b. Tapers (Transition from wide center to narrow ends)
    # Taper width1=center (wide), width2=ends (narrow)
    taper = gf.components.taper(
        length=l_taper,
        width1=h_void_center,
        width2=h_void_ends,
        layer=layer
    )
    
    # Place Right Taper (starts at end of center rect)
    t_right = void << taper
    t_right.movex(l_constant / 2.0)
    
    # Place Left Taper (Mirrored to point left)
    t_left = void << taper
    t_left.mirror()
    t_left.movex(-l_constant / 2.0)
    
    # 2c. Inner Bend Circles (Holes at the ends)
    # These create the constant thickness bend sections
    circ_inner_right = void << gf.components.circle(radius=r_inner, layer=layer)
    circ_inner_right.movex(l_straight / 2.0)
    
    circ_inner_left = void << gf.components.circle(radius=r_inner, layer=layer)
    circ_inner_left.movex(-l_straight / 2.0)

    # --- 3. Create Arm Slots ---
    slots = gf.Component()
    
    # Y Position: Centered in the arm strip
    # Average of inner void edge (1.0) and outer hull edge (1.5) -> 1.25
    y_pos = (h_void_center/2.0 + height/2.0) / 2.0
    
    # X Position: Symmetric around center
    x_offset = slot_gap / 2.0 + slot_len / 2.0
    
    # Create 4 slots (Top-Left, Top-Right, Bot-Left, Bot-Right)
    for y_sign in [-1, 1]:
        for x_sign in [-1, 1]:
            s = slots << gf.components.rectangle(
                size=(slot_len, slot_height), 
                layer=layer, 
                centered=True
            )
            s.move((x_sign * x_offset, y_sign * y_pos))

    # --- 4. Boolean Assembly ---
    # Combine Void geometry and Slots into one negative mask
    negatives = gf.boolean(void, slots, operation="or", layer=layer)
    
    # Subtract negatives from Outer Hull
    final_shape = gf.boolean(outer, negatives, operation="not", layer=layer)
    
    c << final_shape
    return c

if __name__ == "__main__":
    device = device_structure()
    device.write_gds("complex_resonator.gds")
    device.show()