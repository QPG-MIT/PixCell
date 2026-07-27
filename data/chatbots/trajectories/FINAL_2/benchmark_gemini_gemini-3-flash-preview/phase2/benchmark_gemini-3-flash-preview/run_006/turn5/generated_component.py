import gdsfactory as gf

@gf.cell
def generate_final_device():
    """
    Iteration 5: Refining proportions for accuracy.
    - Shortened top tapers, lengthened top straight sections.
    - Center-weighted pin spacing with larger side margins.
    - Shorter, stubbier bottom center pin.
    
    Total Footprint: 25um (width) x 10um (height)
    """
    c = gf.Component("final_device_v5")
    layer = (1, 0)
    
    # --- Vertical Dimension Budget (Total H = 10.0um) ---
    bot_h = 1.0       # Short, stubby bottom pin
    body_h = 4.5      # Main central body
    top_taper_h = 1.2 # Short transition "shoulder"
    top_straight_h = 3.3 # Long thin pins
    # Sum: 1.0 + 4.5 + 1.2 + 3.3 = 10.0 um
    
    # --- Horizontal Dimension Budget (Total W = 25.0um) ---
    body_w = 25.0
    
    # 1. Main Body
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Top Pins (4 units)
    num_pins = 4
    pin_w_base = 2.2  # Wide junction at the body
    pin_w_tip = 0.8   # Thin needle section
    pin_spacing = 5.2 # Clustered more towards the center than previous iteration
    
    # Calculate starting x to center the group of 4
    start_x = - (num_pins - 1) * pin_spacing / 2
    
    for i in range(num_pins):
        x_pos = start_x + i * pin_spacing
        
        # Short Tapered base (The "Shoulder")
        t_ref = c << gf.components.taper(length=top_taper_h, width1=pin_w_base, width2=pin_w_tip, layer=layer)
        t_ref.rotate(90)
        t_ref.move((x_pos, body_h/2))
        
        # Long Straight segment (The "Needle")
        # Placing it precisely at the end of the taper
        s_ref = c << gf.components.rectangle(size=(pin_w_tip, top_straight_h), layer=layer, centered=True)
        s_ref.move((x_pos, body_h/2 + top_taper_h + top_straight_h/2))
        
    # 3. Bottom Pin (Stubby flat taper)
    bot_w_base = 3.2
    bot_w_tip = 1.2
    bot_ref = c << gf.components.taper(length=bot_h, width1=bot_w_base, width2=bot_w_tip, layer=layer)
    bot_ref.rotate(-90)
    bot_ref.move((0, -body_h/2))
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = generate_final_device()
    
    # Export GDS for verification
    device.write_gds("final_device_iteration_5.gds")
    
    # Verification output
    print("--------------------------------------------------")
    print("ITERATION 5: Proportion refinement based on visual feedback.")
    print(f"Total Width: {device.xsize:.2f} um (Target: 25.0)")
    print(f"Total Height: {device.ysize:.2f} um (Target: 10.0)")
    print("Proportion Fixes: Shortened top tapers, elongated pins, stubbier bottom tab.")
    print("--------------------------------------------------")