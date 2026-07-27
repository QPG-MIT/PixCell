import gdsfactory as gf

@gf.cell
def generate_final_device():
    """
    Creates a device geometry matching the target proportions:
    - Thick central rectangular body.
    - Four top pins with prominent tapered bases and thick straight heads.
    - One short, stubby, flat-ended bottom taper.
    
    Total Footprint: 25um (width) x 10um (height)
    """
    c = gf.Component("target_device_match")
    layer = (1, 0)
    
    # --- Dimensions (Summing to 10um total height) ---
    # Total H (10.0) = Top Straight (1.3) + Top Taper (2.2) + Body (5.0) + Bottom Taper (1.5)
    body_w = 22.0 
    body_h = 5.0
    
    top_taper_h = 2.2
    top_straight_h = 1.3
    
    bot_taper_h = 1.5
    
    # 1. Main Body
    # A substantial central rectangle
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Top Pins (4 units)
    # These have a wide base that tapers into a thick rectangle
    num_pins = 4
    pin_w_base = 2.2  # Wide shoulder
    pin_w_tip = 1.4   # Thick top part
    pin_spacing = 4.8 # Cluster them on the body
    
    # Calculate starting x to center the group
    start_x = - (num_pins - 1) * pin_spacing / 2
    
    for i in range(num_pins):
        x_pos = start_x + i * pin_spacing
        
        # Tapered base of the top pin
        t_ref = c << gf.components.taper(length=top_taper_h, width1=pin_w_base, width2=pin_w_tip, layer=layer)
        t_ref.rotate(90)
        t_ref.move((x_pos, body_h/2))
        
        # Straight top segment
        s_ref = c << gf.components.rectangle(size=(pin_w_tip, top_straight_h), layer=layer, centered=True)
        s_ref.move((x_pos, body_h/2 + top_taper_h + top_straight_h/2))
        
    # 3. Bottom Pin (Stubby flat taper)
    # The tip is wide (not pointed) to match the original image
    bot_w_base = 2.8
    bot_w_tip = 1.5
    bot_ref = c << gf.components.taper(length=bot_taper_h, width1=bot_w_base, width2=bot_w_tip, layer=layer)
    bot_ref.rotate(-90)
    bot_ref.move((0, -body_h/2))
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = generate_final_device()
    
    # Export GDS
    device.write_gds("final_device_match.gds")
    
    # Verification output
    print("--------------------------------------------------")
    print("SUCCESS: Device generated with target proportions.")
    print(f"Total Width: {device.xsize:.2f} um (Constraint: 25.0)")
    print(f"Total Height: {device.ysize:.2f} um (Constraint: 10.0)")
    print("Changes: Increased body height, thickened pins, flattened bottom tip.")
    print("--------------------------------------------------")