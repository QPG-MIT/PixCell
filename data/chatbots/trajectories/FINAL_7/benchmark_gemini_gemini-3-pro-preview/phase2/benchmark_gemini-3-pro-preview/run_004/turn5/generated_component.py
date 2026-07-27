import gdsfactory as gf

@gf.cell
def device_structure():
    """
    Constructs a racetrack resonator with variable arm width and slotted straight sections.
    
    Features matched to target:
    - Outer shape: Stadium (Racetrack).
    - Inner shape: 
      - Bends are thick-walled (small inner radius).
      - Straight sections are thin-walled (large inner void).
      - Transition is a linear taper connecting the wide void to the circular bend void.
    - Slots:
      - Located within the thin straight arms.
      - Two distinct rectangular slots per arm.
      - Roughly equal wall thickness above/below slots.
    """
    c = gf.Component()

    # --- Dimensions & Parameters ---
    # Overall Device
    width = 5.5
    height = 3.0
    layer = (1, 0)
    
    # Outer Hull Geometry (Stadium)
    r_outer = height / 2.0           # 1.5 um
    l_straight = width - 2 * r_outer # 2.5 um
    x_bend_center = l_straight / 2.0 # 1.25 um

    # Inner Void Geometry
    # Target: Thick bends, Thin straight arms.
    r_inner_bend = 0.7               # Creates thick bend walls (1.5 - 0.7 = 0.8um)
    arm_width_straight = 0.5         # Creates thin straight walls (0.5um)
    y_inner_straight = r_outer - arm_width_straight # 1.0 um (Void half-height)
    
    # Taper / Transition
    # The void width transitions from y_inner_straight (center) to r_inner_bend (ends).
    # We define a taper start point inside the straight section to allow space for slots.
    # Straight section ends at x = 1.25. Taper length = 0.25um.
    x_taper_start = 1.0 
    
    # Slot Parameters
    slot_len = 0.8
    slot_height = 0.2
    slot_gap = 0.2
    
    # Y-Position of Slots: Centered in the straight arm
    # The arm spans from y = y_inner_straight (1.0) to y = r_outer (1.5).
    # Center y = 1.25.
    y_slot_center = (r_outer + y_inner_straight) / 2.0

    # --- 1. Construct Outer Hull ---
    outer = gf.Component()
    # Central Rectangle
    outer << gf.components.rectangle(size=(l_straight, height), layer=layer, centered=True)
    # End Circles
    c_right = outer << gf.components.circle(radius=r_outer, layer=layer)
    c_right.movex(x_bend_center)
    c_left = outer << gf.components.circle(radius=r_outer, layer=layer)
    c_left.movex(-x_bend_center)

    # --- 2. Construct Inner Void ---
    void = gf.Component()
    
    # 2a. Circular Ends (Holes in the bends)
    v_right = void << gf.components.circle(radius=r_inner_bend, layer=layer)
    v_right.movex(x_bend_center)
    v_left = void << gf.components.circle(radius=r_inner_bend, layer=layer)
    v_left.movex(-x_bend_center)
    
    # 2b. Central Polygon (Main void + Tapers)
    # This polygon connects the wide central void to the circular ends.
    # Vertices are traced clockwise.
    poly_pts = [
        (x_taper_start, y_inner_straight),    # Top Right (Start of Taper)
        (x_bend_center, r_inner_bend),        # Top Right (End of Taper, meeting circle apex)
        (x_bend_center, -r_inner_bend),       # Bottom Right (Meeting circle bottom)
        (x_taper_start, -y_inner_straight),   # Bottom Right (End of Taper)
        (-x_taper_start, -y_inner_straight),  # Bottom Left (Start of Taper)
        (-x_bend_center, -r_inner_bend),      # Bottom Left (Meeting circle bottom)
        (-x_bend_center, r_inner_bend),       # Bottom Left (Meeting circle apex)
        (-x_taper_start, y_inner_straight),   # Top Left (End of Taper)
    ]
    void.add_polygon(points=poly_pts, layer=layer)

    # --- 3. Construct Slots ---
    slots = gf.Component()
    
    # Calculate Slot Positions
    # Center X of slot = gap/2 + len/2
    x_slot_pos = slot_gap / 2.0 + slot_len / 2.0
    
    # Create 4 slots
    for x_sign in [-1, 1]:
        for y_sign in [-1, 1]:
            s = slots << gf.components.rectangle(size=(slot_len, slot_height), layer=layer, centered=True)
            s.move((x_sign * x_slot_pos, y_sign * y_slot_center))

    # --- 4. Boolean Assembly ---
    # Combine Void and Slots into a single "negative" mask
    negatives = gf.boolean(void, slots, operation="or", layer=layer)
    
    # Subtract negatives from the Outer Hull
    final_device = gf.boolean(outer, negatives, operation="not", layer=layer)
    
    c << final_device
    return c

if __name__ == "__main__":
    device = device_structure()
    device.write_gds("complex_resonator.gds")
    device.show()