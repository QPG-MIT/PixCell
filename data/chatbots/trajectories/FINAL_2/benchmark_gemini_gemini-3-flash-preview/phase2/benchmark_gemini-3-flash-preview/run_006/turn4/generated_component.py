import gdsfactory as gf

@gf.cell
def generate_final_device():
    """
    Creates a device matching the target proportions:
    - Wide central rectangular body.
    - Four top pins with prominent tapered bases and thin straight heads.
    - One short, stubby, flat-ended bottom taper.
    
    Total Footprint: 25um (width) x 10um (height)
    """
    c = gf.Component("final_device_v4")
    layer = (1, 0)
    
    # --- Dimensions (Total H = 10.0um) ---
    # Body (3.8) + Top Pins (4.7) + Bottom Pin (1.5) = 10.0
    body_w = 24.0 
    body_h = 3.8
    
    top_taper_h = 3.5
    top_straight_h = 1.2
    
    bot_taper_h = 1.5
    
    # 1. Main Body
    # A wide rectangle that dominates the width
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Top Pins (4 units)
    # These are spread wide across the top surface
    num_pins = 4
    pin_w_base = 2.4  # Wide shoulder at the junction
    pin_w_tip = 0.8   # Thinner tip for the straight part
    pin_spacing = 7.2 # Wide spacing to match target proportions
    
    # Calculate starting x to center the group
    start_x = - (num_pins - 1) * pin_spacing / 2
    
    for i in range(num_pins):
        x_pos = start_x + i * pin_spacing
        
        # Tapered base of the top pin
        t_ref = c << gf.components.taper(length=top_taper_h, width1=pin_w_base, width2=pin_w_tip, layer=layer)
        t_ref.rotate(90)
        t_ref.move((x_pos, body_h/2))
        
        # Straight top segment (needle head)
        s_ref = c << gf.components.rectangle(size=(pin_w_tip, top_straight_h), layer=layer, centered=True)
        s_ref.move((x_pos, body_h/2 + top_taper_h + top_straight_h/2))
        
    # 3. Bottom Pin (Stubby flat taper)
    # Beefy base tapering to a flat, non-pointed tip
    bot_w_base = 3.8
    bot_w_tip = 1.5
    bot_ref = c << gf.components.taper(length=bot_taper_h, width1=bot_w_base, width2=bot_w_tip, layer=layer)
    bot_ref.rotate(-90)
    bot_ref.move((0, -body_h/2))
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = generate_final_device()
    
    # Export GDS
    device.write_gds("final_device_iteration_4.gds")
    
    # Verification output
    print("--------------------------------------------------")
    print("ITERATION 4: Geometry optimized for wide body and pin spacing.")
    print(f"Total Width: {device.xsize:.2f} um (Target: 25.0)")
    print(f"Total Height: {device.ysize:.2f} um (Target: 10.0)")
    print("Proportion Fixes: Flattened body, spread pins, sharpened top tapers.")
    print("--------------------------------------------------")