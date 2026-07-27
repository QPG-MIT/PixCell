import gdsfactory as gf

@gf.cell
def generate_reconstructed_device():
    """
    Recreates the device geometry using parametric primitives.
    Total Footprint: 25um (width) x 10um (height)
    """
    c = gf.Component("reconstructed_device")
    layer = (1, 0)
    
    # --- Dimensions (Optimized for [25, 10] footprint) ---
    # Total Height (10) = Top Pins (3.5) + Body (5.0) + Bottom Pin (1.5)
    body_w = 23.0 
    body_h = 5.0
    top_pin_total_h = 3.5
    bot_pin_h = 1.5
    
    # 1. Main Body
    # Using 'centered=True' as shown in the catalog reference
    body = c << gf.components.rectangle(size=(body_w, body_h), layer=layer, centered=True)
    
    # 2. Top Pins (4 units)
    # Each pin is a combination of a taper and a straight segment
    num_pins = 4
    pin_spacing = body_w / num_pins
    pin_w_base = 1.8
    pin_w_tip = 1.0
    taper_ratio = 0.4 # 40% of pin height is tapered
    
    t_h = top_pin_total_h * taper_ratio
    s_h = top_pin_total_h * (1 - taper_ratio)
    
    for i in range(num_pins):
        # Calculate X center for each pin
        x_pos = -body_w/2 + (i + 0.5) * pin_spacing
        
        # Tapered base of the pin
        # Origin of taper is center of width1. Rotate 90 to point up.
        taper_ref = c << gf.components.taper(length=t_h, width1=pin_w_base, width2=pin_w_tip, layer=layer)
        taper_ref.rotate(90)
        taper_ref.move((x_pos, body_h/2))
        
        # Straight top of the pin
        # Origin is center. Move to sit exactly on top of the taper.
        straight_ref = c << gf.components.rectangle(size=(pin_w_tip, s_h), layer=layer, centered=True)
        straight_ref.move((x_pos, body_h/2 + t_h + s_h/2))
        
    # 3. Bottom Pin (Single Taper)
    # Pointing downwards (rotate -90)
    bot_ref = c << gf.components.taper(length=bot_pin_h, width1=2.5, width2=1.0, layer=layer)
    bot_ref.rotate(-90)
    bot_ref.move((0, -body_h/2))
    
    return c

if __name__ == "__main__":
    # Create component
    device = generate_reconstructed_device()
    
    # Output GDS file (Corrected: ensure this line is active)
    device.write_gds("device_layout.gds")
    
    # Feedback
    print("--------------------------------------------------")
    print("SUCCESS: 'device_layout.gds' has been produced.")
    print(f"Final Footprint: {device.xsize:.2f} um (W) x {device.ysize:.2f} um (H)")
    print("--------------------------------------------------")